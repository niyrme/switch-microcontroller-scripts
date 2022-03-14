import cv2

from lib import getframe


def main() -> int:
	print("setting up cv2. This may take a while...")
	vid: cv2.VideoCapture = cv2.VideoCapture(0)
	vid.set(cv2.CAP_PROP_FPS, 30)
	vid.set(cv2.CAP_PROP_FRAME_WIDTH, 768)
	vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
	print("\033c", end="")

	try:
		while True:
			getframe(vid)
	except KeyboardInterrupt:
		pass
	finally:
		vid.release()
		cv2.destroyAllWindows()

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
