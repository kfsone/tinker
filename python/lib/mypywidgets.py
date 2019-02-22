#! /usr/bin/env python3

"""
My ipywidgets helpers to produce simple controls that use available space
"""

import ipywidgets
from ipywidgets import IntProgress, FloatProgress, HBox, Label, Layout, IntSlider, FloatSlider
from IPython.display import display
from typing import Union


class Presenter(object):
    """
    Base class for displaying a standard widget with annotation, in the form:
    <title> <widget> <info>
    """

    left_layout  = Layout(width='65%')
    right_layout = Layout(width='35%')
    box_layout   = Layout(width='100%')

    
    def __init__(self, title: str, max: Union[int, float], min: Union[int, float] = 0, **klsargs) -> None:
        self.data  = self.CLASS(min=min, max=max, layout=self.left_layout, description=title, **klsargs)
        self.label = Label(value='Starting', layout=self.right_layout)
        self.hbox  = HBox([self.data, self.label], layout=self.box_layout)

        
    def display(self) -> None:
        """ Show the widget """
        display(self.hbox)

        
    def increment(self, inc: Union[int, float], suffix: str = "") -> None:
        """ Adjust the value of the widget """
        data = self.data
        data.value += inc
        self.label.value = "{:6.2f}% :: {:,}/{:,} {}".format(
            (data.value * 100) / data.max,
            int(data.value / self.units),
            self.umax,
            suffix,
        )

        
class ProgressBar(Presenter):
    """ Integer progress bar helper """
    CLASS = IntProgress

    def __init__(self, title: str, max: Union[int, float], units: int = 1, **kwargs) -> None:
        super().__init__(title, max, bar_style='info')
        self.units = units or 1
        self.umax  = int(self.data.max / self.units)

        
class ProgressBarF(ProgressBar):
    """ Float progress bar helper """
    CLASS = FloatProgress

    
class Slider(Presenter):
    """ Integer slider helper """
    CLASS = IntSlider

    def __init__(self, title: str, max: Union[int, float], min: Union[int, float] = 0, default: Union[int, float] = min, **kwargs) -> None:
        super().__init__(title, max, min=min, value=default, **kwargs)
        self.data.value = default

        
class SliderF(Slider):
    """ Float slider helper """
    CLASS = FloatSlider
    

# Example usage:
# 
# pb_kb = ProgressBarF("Progress", max=100., units=1024)
# pb_kb.display()
#
# for i in range(0, 100, .1):
#  pb_kb.increment(0.1)
#  time.sleep(0.01)

