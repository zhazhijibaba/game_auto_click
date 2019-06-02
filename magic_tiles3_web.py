import numpy as np
from PIL import ImageGrab
import mss
import cv2
from pynput.mouse import Button, Controller
import time
import sys

# origin position of the game play screen
# you can modify this parameter according to your own computer
ox = 44
oy = 132
# the position and size for screen capture
# you can modify this parameter according to your own computer
gameBox = {"top": 132, "left": 44, "width": 390, "height": 650}
# four x positions to check piano key dropping
lines = [98, 294, 490, 686]
mouse = Controller()

# find and update mouse position and perform clicking
def click_box_new(new_screen):
    # find the unclicked black piano keys
    ii = np.nonzero(new_screen[:, lines] < 100)
    # return if all keys have been already clicked
    if len(ii[0]) == 0:
        return
    # find the button position of the key
    j = np.argmax(ii[0])
    y = ii[0][j]
    x = lines[ii[1][j]]
    # compute the realy mouse position
    xx = ox + x / 2
    yy = oy + y / 2 + 10
    # only click the position inside the game play screen
    # you can modify this parameter according to your own computer
    if yy > 786 or yy < 180:
        return
    if xx < 60  or xx > 425:
        return
    # update mouse position and perform mouse clicking
    mouse.position = (xx, yy)
    print mouse.position, xx, yy
    mouse.click(Button.left, 1)
    #time.sleep(0.1)
    return

def main():

    # wait for 2 seconds before press start button
    time.sleep(2)
    mouse.click(Button.left, 1)

    # main loop
    for i in range(100000):
        # screen capture
        with mss.mss() as sct:
            screen = np.array(sct.grab(gameBox))
        # convert the color screen to gray
        new_screen = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)
        # perform mouse clicking
        click_box_new(new_screen)
        # move the mouse away to stop the program
        if mouse.position[0] > 500:
            break
        #if cv2.waitKey(25) & 0xFF == ord('q'):
        #    cv2.destroyAllWindows()
        #    break

if __name__ == "__main__":
    main()
