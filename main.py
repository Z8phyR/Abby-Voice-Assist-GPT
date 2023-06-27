import threading
import Abby
import abby_gui

def main():
    # Start Abby in a new thread
    abby_thread = threading.Thread(target=Abby.start_listening)
    abby_thread.start()

    # Start GUI in the main thread
    abby_gui.start_gui()

if __name__ == "__main__":
    main()