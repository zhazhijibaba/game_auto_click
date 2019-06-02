import numpy as np
from numpy.linalg import eig, inv
import mss
import cv2
import imutils
from pynput.mouse import Button, Controller
import time
import sys
import argparse

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--debug", required=False, help="debug mode", action="store_true")
ap.add_argument("-t", "--detect", required=False, help="detect mode", action="store_true")
ap.add_argument("-n", "--nstep", required=False, help="number of steps", default=1, type=int)
ap.add_argument("-g", "--gamma", required=False, help="gamma value for contrast", default=1.8, type=float)
ap.add_argument("-u", "--user", required=False, help="user picking mode", action="store_true")
args = vars(ap.parse_args())
DEBUG= args["debug"]
DETECT= args["detect"]

# origin position of the game play screen
# you can modify this parameter according to your own computer
ox = 552
oy = 154
# the position and size for screen capture
# you can modify this parameter according to your own computer
gameBox = {"top": 132, "left": 44, "width": 390, "height": 650}
gameBox = {"top": 154, "left": 552, "width": 348, "height": 630}
# middle position of the game play screen
MIDDLE = 348
# hight of the black jumper
HEIGHT = 106

mouse = Controller()

def detect_target_position(image, gray, start_position, canny_p1, canny_p2):
    # find the edges
    edges = cv2.Canny(gray, canny_p1, canny_p2)
    # get the contours based on the edges
    cnts = cv2.findContours(edges.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    if DEBUG:
        cv2.imshow("Image", edges)
        cv2.waitKey(0)
    # grab contours
    cnts = imutils.grab_contours(cnts)
    canvas  = image.copy()
    Y_min = start_position[1]
    x_top = 10000
    y_top = 10000
    for c in cnts:
        # find the top point
        y_min = np.min(np.array(c), axis=0)
        # the point should within the game play screen
        if y_min[0, 1] < 232 or y_min[0, 1] > 1068:
            continue
        # the top point should be higher than the starting point
        if y_min[0, 1] < start_position[1]:
            # find the toppest point position
            i = np.argmin(np.array(c), axis=0)
            xt_top = c[i[0, 1]][0][0]
            yt_top = c[i[0, 1]][0][1]
            # the start point and the target point should be in different sides
            if start_position[0] < MIDDLE:
                if xt_top < MIDDLE:
                    continue
            if start_position[0] > MIDDLE:
                if xt_top > MIDDLE:
                    continue
            Y_min = y_min[0, 1]
            x_top = xt_top
            y_top = yt_top
    if DEBUG:
        print "top position", x_top, y_top
        # draw the contour and center of the shape on the image
        cv2.drawContours(canvas, [c], -1, (0, 255, 0), 2)
        cv2.circle(canvas, (x_top, y_top), 7, (0, 255, 0), -1)
        cv2.imshow("Image", canvas)
        cv2.waitKey(0)
    # compute the target point position according to the top point
    xt = x_top
    yt = int(start_position[1] - np.abs(start_position[0] - xt) / np.sqrt(3))
    # reposition the target point. in the middle of the toppest point and the original target
    xt = int (0.5 * xt + 0.5 * x_top)
    yt = int (0.5 * yt + 0.5 * y_top)
    if DEBUG:
        print "target position", xt, yt
    return xt, yt

def detect_start_position(image, gray, dp, md, gray_flag=False):
    # use gray picture
    if gray_flag:
        edges = gray.copy()
    else:
        # use edges
        edges = cv2.Canny(gray, 30, 40)
    if DEBUG:
        #cv2.imshow("Image", gray)
        cv2.imshow("Image", edges)
        cv2.waitKey(0)
        output = image.copy()
    # detect circles in the image
    circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, dp, md, param1=50,param2=30,minRadius=0,maxRadius=50)
    if circles is None:
        print "Not circle found"
    # ensure at least some circles were found
    if circles is not None:
        # convert the (x, y) coordinates and radius of the circles to integers
        circles = np.round(circles[0, :]).astype("int")
        # loop over the (x, y) coordinates and radius of the circles
        Y_min = 1000
        xs = -1
        ys = -1
        for (x, y, r) in circles:
            # draw the circle in the output image, then draw a rectangle
            # corresponding to the center of the circle
            if y < 232 or y > 800:
                continue
            dr = np.abs(r - 18)
            # the radius difference should be less than 2
            if dr > 2:
                continue
            # update the top point
            if ys < Y_min:
                Y_min = y
                xs = x
                ys = y
            if DEBUG:
                print x, y, r, dr
                cv2.circle(output, (x, y), r, (0, 255, 0), 4)
                cv2.rectangle(output, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)

        # show the output image
        if DEBUG:
            cv2.imshow("Image", np.hstack([image, output]))
            cv2.waitKey(0)
        # find the start point according th the height of the jumper
        ys = ys + HEIGHT
        print "start position", xs, ys
        return xs, ys

def compute_jump_time(start_position, target_position):
    p1 = start_position
    p2 = target_position
    dist2 = (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2
    jump_time = np.sqrt(dist2) * 0.00201
    return jump_time

def auto_click(screen_original):
    screen = adjust_gamma(screen_original, args["gamma"])
    new_screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
    # find start position
    dp_md_pair = [(1.2, 100), (1.0, 100), (0.8, 100), (0.6, 100), (0.4, 100), (0.2, 100),
            (1.4, 100), (1.6, 100), (1.8, 100), (2.0, 100), (2.2, 100), (2.4, 100),
            (1.2, 200), (1.2, 300), (1.2, 400), (1.0, 200), (1.0, 300), (1.0, 400)]
    for dp, md in dp_md_pair:
        start_position = detect_start_position(screen, new_screen, dp, md, True)
        if start_position[0] > 0:
            break
        start_position = detect_start_position(screen, new_screen, dp, md)
        if start_position[0] > 0:
            break
        start_position = detect_start_position(screen, new_screen, dp, md)

    # find target position
    if args["user"]:
        # user picking mode
        xx, yy = mouse.position
        x = 2 * int(xx - ox)
        y = 2 * int(yy - oy)
        target_position = x, y
    else:
        target_positions = []
        for d in [0, 0.2, 0.4]:
            screen = adjust_gamma(screen_original, args["gamma"] + d)
            new_screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
            target_position1 = detect_target_position(screen, new_screen, start_position, 15, 20)
            new_screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
            target_position2 = detect_target_position(screen, new_screen, start_position, 5, 10)
            target_positions.append(target_position2)
        #print target_positions
        target_positions = sorted(target_positions, key=lambda k: k[1])
        target_position = target_positions[0]
        print "target position", target_position
    # if it is faild to find start and target point, jump a tiny step
    if start_position[0] < 0 or target_position[0] < 0:
        jump_time = 0.0001
    else:
        jump_time = compute_jump_time(start_position, target_position)
    print "jump time {0}".format(jump_time)
    if DEBUG or DETECT:
        # draw the contour and center of the start and target position
        canvas = screen.copy()
        print start_position
        cv2.circle(canvas, (start_position[0], start_position[1]), 7, (255, 0, 0), -1)
        print target_position
        cv2.circle(canvas, (target_position[0], target_position[1]), 7, (0, 0, 255), -1)
        cv2.imshow("Image", canvas)
        cv2.waitKey(0)
    else:
        mouse.press(Button.left)
        time.sleep(jump_time)
        mouse.release(Button.left)
    return

# adjust pisture contract, make background lighter
def adjust_gamma(image, gamma=1.0):
	# build a lookup table mapping the pixel values [0, 255] to
	# their adjusted gamma values
	invGamma = 1.0 / gamma
	table = np.array([((i / 255.0) ** invGamma) * 255
		for i in np.arange(0, 256)]).astype("uint8")
	# apply gamma correction using the lookup table
	return cv2.LUT(image, table)

def main():

    # wait to start
    time.sleep(2)

    # main loop
    for i in range(args["nstep"]):
        # screen capture according to game play screen
        with mss.mss() as sct:
            screen = np.array(sct.grab(gameBox))
        # perform auto clicking
        auto_click(screen)
        # no waiting time if there is only one step
        if args["nstep"] > 1:
            time.sleep(4)
        #if cv2.waitKey(25) & 0xFF == ord('q'):
        #    cv2.destroyAllWindows()
        #    break

if __name__ == "__main__":
    main()
