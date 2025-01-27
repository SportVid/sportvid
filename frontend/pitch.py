# import packages
import pandas as pd
import numpy as np
from floodlight.vis.pitches import plot_football_pitch
from floodlight.vis.positions import plot_trajectories
from mplsoccer import Pitch
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('module://backend_interagg')

def visualize_pitch():
    # create pitch
    pitch = Pitch(pitch_type="custom", pitch_length=100, pitch_width=65, line_alpha=0.8, line_color="black", pitch_color="white", corner_arcs=True, linewidth=0.4)
    fig, ax = pitch.draw(figsize=(10, 7))

    # add outside line
    floater_pitch = plt.Rectangle((0, 0), 100, 65, edgecolor="black", facecolor="none", linewidth=1)
    ax.add_patch(floater_pitch)

    # add goal line
    ax.plot([0, 0], [32.5 - 3.66, 32.5 + 3.66], color="black", linewidth=2.5)
    ax.plot([100, 100], [32.5 - 3.66, 32.5 + 3.66], color="black", linewidth=2.5)

    plt.show()

    return fig

graphic_pitch = visualize_pitch()
graphic_pitch.savefig("pitch.png", dpi=300)