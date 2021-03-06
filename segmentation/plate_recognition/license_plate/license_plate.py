# import the necessary packages
from collections import namedtuple
from skimage.filters import threshold_adaptive
from skimage import segmentation
from skimage import measure
from imutils import perspective
import numpy as np
import imutils
import cv2

# define the named tupled to store the license plate
LicensePlate = namedtuple("LicensePlateRegion", ["success", "plate", "thresh", "candidates", "chars", "wb"])


class LicensePlateDetector:
    def __init__(self, image, lpNumber, minPlateW=60, minPlateH=20, numChars=8, minCharW=40):
        # store the image to detect license plates in, the minimum width and height of the
        # license plate region, the number of characters to be detected in the license plate,
        # and the minimum width of the extracted characters
        self.image = image
        self.lpNumber = lpNumber
        self.minPlateW = minPlateW
        self.minPlateH = minPlateH
        self.numChars = numChars
        self.minCharW = minCharW

    def detectCharacterCandidates(self):
        # apply a 4-point transform to extract the license plate
        plate = self.image#perspective.four_point_transform(self.image, region)
        # cv2.imshow("Perspective Transform", imutils.resize(plate, width=400))
        # cv2.waitKey(0)

        # extract the Value component from the HSV color space and apply adaptive thresholding
        # to reveal the characters on the license plate
        V = cv2.split(cv2.cvtColor(plate, cv2.COLOR_BGR2HSV))[2]
        thresh = threshold_adaptive(V, 25, offset=15).astype("uint8") * 255
        thresh = cv2.bitwise_not(thresh)

        # resize the license plate region to a canonical size
        plate = imutils.resize(plate, width=400)
        thresh = imutils.resize(thresh, width=400)
        # cv2.imwrite("./bad_black_letters/{}.jpg".format(self.lpNumber), cv2.bitwise_not(thresh))
        # cv2.imshow("Thresh", thresh)
        # cv2.waitKey(0)
        # perform a connected components analysis and initialize the mask to store the locations
        # of the character candidates
        labels = measure.label(thresh, neighbors=8, background=0)
        charCandidates = np.zeros(thresh.shape, dtype="uint8")

        # loop over the unique components
        for label in np.unique(labels):
            # if this is the background label, ignore it
            if label == 0:
                continue

            # otherwise, construct the label mask to display only connected components for the
            # current label, then find contours in the label mask
            labelMask = np.zeros(thresh.shape, dtype="uint8")
            labelMask[labels == label] = 255
            if cv2.__version__ == "3.4.2":
                (_, cnts, _) = cv2.findContours(labelMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            elif cv2.__version__ == "4.0.0":
                cnts, _ =  cv2.findContours(labelMask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # ensure at least one contour was found in the mask
            if len(cnts) > 0:
                # grab the largest contour which corresponds to the component in the mask, then
                # grab the bounding box for the contour
                c = max(cnts, key=cv2.contourArea)
                (boxX, boxY, boxW, boxH) = cv2.boundingRect(c)

                # compute the aspect ratio, solidity, and height ratio for the component
                aspectRatio = boxW / float(boxH)
                solidity = cv2.contourArea(c) / float(boxW * boxH)
                heightRatio = boxH / float(plate.shape[0])

                # determine if the aspect ratio, solidity, and height of the contour pass
                # the rules tests
                keepAspectRatio = aspectRatio < 1.0
                keepSolidity = solidity > 0.15
                keepHeight = heightRatio > 0.4 and heightRatio < 0.95

                # check to see if the component passes all the tests
                if keepAspectRatio and keepSolidity and keepHeight:
                    # compute the convex hull of the contour and draw it on the character
                    # candidates mask
                    hull = cv2.convexHull(c)
                    cv2.drawContours(charCandidates, [hull], -1, 255, -1)

        # clear pixels that touch the borders of the character candidates mask and detect
        # contours in the candidates mask
        charCandidates = segmentation.clear_border(charCandidates)
        # (_, cnts, _) = cv2.findContours(charCandidates.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if cv2.__version__ == "3.4.2":
            (_, cnts, _) = cv2.findContours(charCandidates.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        elif cv2.__version__ == "4.0.0":
            cnts, _ = cv2.findContours(charCandidates.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cv2.imshow("Original Canedidates", charCandidates)
        # cv2.waitKey(0)


        # print(self.lpNumber)
        plate1 = plate
        chars = []
        lp_characters_coords = sorted([cv2.boundingRect(cnts[i]) for i in range(len(cnts))], key=lambda x: x[0])
        # print(len(lp_characters_coords))
        # if len(lp_characters_coords) == self.numChars:
        for i in range(len(lp_characters_coords)):
            xx, yy, ww, hh = lp_characters_coords[i]
            # character_filename = "dataset3/{}_{}_{}.jpg".format(self.lpNumber[i], self.lpNumber, i)
            # cv2.imwrite(character_filename, plate1[yy:yy + hh + 5, xx:xx + ww])
            cv2.imshow("o", plate1[yy:yy + hh + 5, xx:xx + ww])
            cv2.waitKey(0)

            chars.append(plate1[yy:yy + hh + 5, xx:xx + ww])

        # take bitwise AND of the raw thresholded image and character candidates to get a more
        # clean seqmentation of the characters
        thresh = cv2.bitwise_and(thresh, thresh, mask=charCandidates)
        wb = cv2.bitwise_not(thresh)
        # cv2.imwrite("./bad_black_letters/{}.jpg".format(self.lpNumber), cv2.bitwise_not(thresh))
        # cv2.imshow("Char Threshold", thresh)
        # cv2.waitKey(0)

        # return the license plate region object containing the license plate, the thresholded
        # license plate, and the character candidates
        return LicensePlate(success=True, plate=plate, thresh=thresh,
                            candidates=charCandidates, chars=chars, wb=wb)
