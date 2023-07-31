import keyboard


class Sound:
    """
    Class Sound
    :author: Paradoxis <luke@paradoxis.nl>
    :description:

    Allows you control the Windows volume
    The first time a sound method is called, the system volume is fully reset.
    This triggers sound and mute tracking.
    """

    # Current volume, we will set this to 100 once initialized
    __current_volume = None

    @staticmethod
    def current_volume():
        """
        Current volume getter
        :return: int
        """
        if Sound.__current_volume is None:
            return 0
        else:
            return Sound.__current_volume

    @staticmethod
    def __set_current_volume(volume):
        """
        Current volumne setter
        prevents numbers higher than 100 and numbers lower than 0
        :return: void
        """
        if volume > 100:
            Sound.__current_volume = 100
        elif volume < 0:
            Sound.__current_volume = 0
        else:
            Sound.__current_volume = volume


    # The sound is not muted by default, better tracking should be made
    __is_muted = False

    @staticmethod
    def is_muted():
        """
        Is muted getter
        :return: boolean
        """
        return Sound.__is_muted


    @staticmethod
    def __track():
        """
        Start tracking the sound and mute settings
        :return: void
        """
        if Sound.__current_volume == None:
            Sound.__current_volume = 0
            for i in range(0, 50):
                Sound.volume_up()


    @staticmethod
    def mute():
        """
        Mute or un-mute the system sounds
        Done by triggering a fake VK_VOLUME_MUTE key event
        :return: void
        """
        Sound.__track()
        Sound.__is_muted = (not Sound.__is_muted)
        keyboard.press("volume_mute")

    @staticmethod
    def volume_up():
        """
        Increase system volume
        Done by triggering a fake VK_VOLUME_UP key event
        :return: void
        """
        Sound.__track()
        Sound.__set_current_volume(Sound.current_volume() + 2)
        keyboard.press("volume_up")

    @staticmethod
    def volume_down():
        """
        Decrease system volume
        Done by triggering a fake VK_VOLUME_DOWN key event
        :return: void
        """
        Sound.__track()
        Sound.__set_current_volume(Sound.current_volume() - 2)
        keyboard.press("volume_down")


    @staticmethod
    def volume_set(amount):
        """
        Set the volume to a specific volume, limited to even numbers.
        This is due to the fact that a VK_VOLUME_UP/VK_VOLUME_DOWN event increases
        or decreases the volume by two every single time.
        :return: void
        """
        Sound.__track()

        if Sound.current_volume() > amount:
            for i in range(0, int((Sound.current_volume() - amount) / 2)):
                Sound.volume_down()
        else:
            for i in range(0, int((amount - Sound.current_volume()) / 2)):
                Sound.volume_up()

    @staticmethod
    def volume_min():
        """
        Set the volume to min (0)
        :return: void
        """
        Sound.volume_set(0)

    @staticmethod
    def volume_max():
        """
        Set the volume to max (100)
        :return: void
        """
        Sound.volume_set(100)