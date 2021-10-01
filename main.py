import streamlink
import vlc
from pprint import pprint

# streams = streamlink.streams("https://www.youtube.com/watch?v=MDHIdUMpunI")

import sys

from PySide6.QtCore import QStandardPaths, Qt, Slot
from PySide6.QtGui import QAction, QIcon, QKeySequence, QScreen
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow, QSlider, QStyle, QToolBar
from PySide6.QtMultimedia import QAudio, QAudioOutput, QMediaFormat, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

AVI = "video/x-msvideo"  
MP4 = 'video/mp4'

def get_supported_mime_types():
    result = []
    for f in QMediaFormat().supportedFileFormats(QMediaFormat.Decode):
        mime_type = QMediaFormat(f).mimeType()
        result.append(mime_type.name())
    return result


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        
        ########

        #self.hide_grips = True 
        self.show()

        #########
        self._playlist = [] 
        self._playlist_index = -1
        self._audio_output = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._player.isSeekable = True
        
        self._player.errorOccurred.connect(self._player_error)

        tool_bar = QToolBar()
        self.addToolBar(tool_bar)

        icon = QIcon.fromTheme("document-open")
        open_action = QAction(icon, "&Open...", self, shortcut=QKeySequence.Open, triggered=self.open)

        tool_bar.addAction(open_action)
        icon = QIcon.fromTheme("application-exit")
        exit_action = QAction(icon, "E&xit", self, shortcut="Ctrl+Q", triggered=self.close)

        style = self.style()
        icon = QIcon.fromTheme("media-playback-start.png", style.standardIcon(QStyle.SP_MediaPlay))
        self._play_action = tool_bar.addAction(icon, "Play")
        self._play_action.triggered.connect(self._player.play)

        icon = QIcon.fromTheme("media-skip-backward-symbolic.svg", style.standardIcon(QStyle.SP_MediaSkipBackward))
        self._previous_action = tool_bar.addAction(icon, "Previous")
        self._previous_action.triggered.connect(self.previous_clicked)

        icon = QIcon.fromTheme("media-playback-pause.png", style.standardIcon(QStyle.SP_MediaPause))
        self._pause_action = tool_bar.addAction(icon, "Pause")
        self._pause_action.triggered.connect(self._player.pause)

        icon = QIcon.fromTheme("media-skip-forward-symbolic.svg", style.standardIcon(QStyle.SP_MediaSkipForward))
        self._next_action = tool_bar.addAction(icon, "Next")
        self._next_action.triggered.connect(self.next_clicked)

        icon = QIcon.fromTheme("media-playback-stop.png", style.standardIcon(QStyle.SP_MediaStop))
        self._stop_action = tool_bar.addAction(icon, "Stop")
        self._stop_action.triggered.connect(self._ensure_stopped)

        self._volume_slider = QSlider()
        self._volume_slider.setOrientation(Qt.Horizontal)
        self._volume_slider.setMinimum(0)
        self._volume_slider.setMaximum(100)
        available_width = self.screen().availableGeometry().width()
        self._volume_slider.setFixedWidth(available_width / 10)
        self._volume_slider.setValue(self._audio_output.volume()*100)
        self._volume_slider.setTickInterval(10)
        self._volume_slider.setTickPosition(QSlider.TicksBelow)
        self._volume_slider.setToolTip("Volume")
        self._volume_slider.valueChanged.connect(self.setVolume)# self._audio_output.setVolume
        tool_bar.addWidget(self._volume_slider)
        print("Volume : " + str(self._audio_output.volume ))
        
        self._video_widget = QVideoWidget()
        self.setCentralWidget(self._video_widget)
        self._player.playbackStateChanged.connect(self.update_buttons)
        
        self._player.setVideoOutput(self._video_widget)

        self.update_buttons(self._player.playbackState())
        self._mime_types = []

        self.__timeSlider = QSlider()
        self.__timeSlider.setOrientation(Qt.Horizontal)
        self.__timeSlider.setMinimum(0)
        self.__timeSlider.setMaximum(self._player.duration())
        self.__timeSlider.setFixedWidth(available_width / 10)
        self.__timeSlider.setValue(0)
        tool_bar.addWidget(self.__timeSlider)

        self._player.durationChanged.connect(self.change_duration)
        self._player.positionChanged.connect(self.change_position)
        self.__timeSlider.sliderMoved.connect(self.video_position)
#
#
    @Slot()
    def change_position(self, position):
        self.__timeSlider.setValue(position)
        
    @Slot()
    def change_duration(self, duration):
        self.__timeSlider.setRange(0, duration)

    @Slot()
    def video_position(self, position):
        self._player.setPosition(position)
        print(position)

    def setVolume(self,value):
        linearVolume = QAudio.convertVolume( value / 100.0, QAudio.LogarithmicVolumeScale, QAudio.LinearVolumeScale);
        # print("before : " + str(value) + " after : " + str(linearVolume))
        self._audio_output.setVolume(linearVolume)

    def test(self,value):
        print(value)
        

    def printt(self,a):
        print(dir(self))
        print(a.__dict__)

    def closeEvent(self, event):
        self._ensure_stopped()
        event.accept()

    @Slot()
    def open(self):
        self._ensure_stopped()
        file_dialog = QFileDialog(self)

        is_windows = sys.platform == 'win32'
        if not self._mime_types:
            self._mime_types = get_supported_mime_types()
            if (is_windows and AVI not in self._mime_types):
                self._mime_types.append(AVI)
            elif MP4 not in self._mime_types:
                self._mime_types.append(MP4)

        file_dialog.setMimeTypeFilters(self._mime_types)

        default_mimetype = AVI if is_windows else MP4
        if default_mimetype in self._mime_types:
            file_dialog.selectMimeTypeFilter(default_mimetype)

        movies_location = QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)
        file_dialog.setDirectory(movies_location)
        if file_dialog.exec() == QDialog.Accepted:
            url = file_dialog.selectedUrls()[0]
            self._playlist.append(url)
            self._playlist_index = len(self._playlist) - 1
            self._player.setSource(url)
            self._player.play()

    @Slot()
    def _ensure_stopped(self):
        if self._player.playbackState() != QMediaPlayer.StoppedState:
            self._player.stop()

    @Slot()
    def previous_clicked(self):
        # Go to previous track if we are within the first 5 seconds of playback
        # Otherwise, seek to the beginning.
        if self._player.position() <= 5000 and self._playlist_index > 0:
            self._playlist_index -= 1
            self._playlist.previous()
            self._player.setSource(self._playlist[self._playlist_index])
        else:
            self._player.setPosition(0)

    @Slot()
    def next_clicked(self):
        if self._playlist_index < len(self._playlist) - 1:
            self._playlist_index += 1
            self._player.setSource(self._playlist[self._playlist_index])

    def update_buttons(self, state):
        media_count = len(self._playlist)
        self._play_action.setEnabled(media_count > 0
            and state != QMediaPlayer.PlayingState)
        self._pause_action.setEnabled(state == QMediaPlayer.PlayingState)
        self._stop_action.setEnabled(state != QMediaPlayer.StoppedState)
        self._previous_action.setEnabled(self._player.position() > 0)
        self._next_action.setEnabled(media_count > 1)

    def show_status_message(self, message):
        self.statusBar().showMessage(message, 5000)

    @Slot(QMediaPlayer.Error, str)
    def _player_error(self, error, error_string):
        print(error_string, file=sys.stderr)
        self.show_status_message(error_string)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    main_win = MainWindow()
    main_win.setWindowTitle("SnowV")
    available_geometry = main_win.screen().availableGeometry()
    main_win.resize(available_geometry.width() / 3,
                    available_geometry.height() / 2)
    
    


    sys.exit(app.exec())
    