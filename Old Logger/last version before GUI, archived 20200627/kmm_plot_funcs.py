# import matplotlib.pyplot as plt


def make_mag_plot(plotter, data):
    if not plotter.initialized:
        if plotter.show:
            plotter.fig.show()
        ax_mag_x = plotter.fig.add_subplot(3, 1, 1)
        ax_mag_y = plotter.fig.add_subplot(3, 1, 2)
        ax_mag_z = plotter.fig.add_subplot(3, 1, 3)
        plotter.fig.tight_layout()
        plotter.axes = [ax_mag_x, ax_mag_y, ax_mag_z]
        plotter.initialized = True

    for idx, ax in enumerate(plotter.axes):
        ax.cla()
        data.iloc[:, idx].plot(ax=ax, marker='.', linestyle='None')
        ax.set_ylabel(plotter.save_group.channels[idx].chan_name + '( mG)')
        if idx != 2:
            ax.set_xlabel(None)
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel(plotter.xlabel)


def make_ion_gauge_plot(plotter, data):
    if not plotter.initialized:
        plotter.ax = plotter.fig.add_subplot(1, 1, 1)
        if plotter.show:
            plotter.fig.show()
        plotter.initialized = True
    plotter.ax.cla()
    (10**data).plot(ax=plotter.ax, marker='.', linestyle='None')
    plotter.ax.set_xlabel(plotter.xlabel)
    plotter.ax.set_ylabel('Ion Gauge Pressure (torr)')
    plotter.ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0))
    plotter.ax.set_yscale('log')
    # plotter.ax.set_ylim(1e-10,4e-10)


def make_ion_pump_plot(plotter, data):
    if not plotter.initialized:
        plotter.ax = plotter.fig.add_subplot(1, 1, 1)
        plotter.ax2 = plotter.ax.twinx()
        if plotter.show:
            plotter.fig.show()
        plotter.initialized = True
    plotter.ax.cla()
    ((10.0**9.0)*(10.0**data)).plot(ax=plotter.ax, marker='.', linestyle='None')
    plotter.ax.set_xlabel(plotter.xlabel)
    plotter.ax.set_ylabel('Ion Pump Current (nA)')

    def curr2press(curr):
        # formula given in ion pump controller to convert current (expressed in nA) to pressure (in torr)
        return 0.066*curr*10**-9*5600/7000/70
    ymin, ymax = plotter.ax.get_ylim()
    plotter.ax2.set_ylim(curr2press(ymin), curr2press(ymax))
    plotter.ax2.set_ylabel('Pressure (torr)')
