from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtGui import QMovie
from PyQt5.QtCore import QTimer, QThread, pyqtSignal
import Abby
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

config.read('config.txt')
NAME = config.get('General','Name')

class AbbyThread(QThread):
    update_state_signal = pyqtSignal(str)  # Create a new signal

    def run(self):
        Abby.start_listening()

class MainWindow(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{NAME} Voice Assistant")

        self.animations = {
            'listening': QMovie('content/abby_listening.gif'),
            'speaking': QMovie('content/abby_talking.gif'),
            'idle': QMovie('content/abby_idle.gif'),
        }

        self.set_state('idle')  # Start with the 'idle' animation

        # Set up a timer to check if Abby is exiting
        self.exit_timer = QTimer()
        self.exit_timer.timeout.connect(self.check_exit)
        self.exit_timer.start(100)  # Check every 100ms

    def set_state(self, state):
        self.setMovie(self.animations[state])
        self.movie().start()

    def check_exit(self):
        if Abby.is_exiting:
            self.exit_timer.stop()  # Stop checking for exit
            QApplication.quit()  # Close the application

def start_gui():
    app = QApplication([])

    main_win = MainWindow()
    main_win.show()
    
    # Create Abby thread and connect the signal
    abby_thread = AbbyThread()
    abby_thread.update_state_signal.connect(main_win.set_state)
    Abby.set_state = abby_thread.update_state_signal.emit  # Change set_state() to emit the signal

    abby_thread.start()
    app.exec_()

start_gui()
