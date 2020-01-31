
import cartopy
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from convertbng.util import convert_bng, convert_lonlat

from dbconnector import DBConnector

class PlotPassivSystems:

    """A class to plot the passiv system on a map using plotly."""

    def __init__(self):
        self.mysql_defaults = "../data/mysql_defaults/mysql_defaults." \
                              "ssfdb2.readonly_xoolon.pvstream"
        self.mapbox_token = "pk.eyJ1Ijoib2h1eCIsImEiOiJjazV6NTIyZWswN2" \
                            "IwM3BvMXJpZmk3eDY0In0.3rfKBtnKrLCrihBzLi8zOg"
        self.data = None

    def download_passiv_systems(self):
        with DBConnector(mysql_defaults=self.mysql_defaults,
                         session_tz="UTC") as dbc:
            sql = "SELECT `latitude`, `longitude`, `kWp` " \
                  "FROM pvstream.view_system_params_grouped_op_at;"
            data = dbc.query(sql, df=True)
        self.data = data
        return data

    def plot_maps(self, number_of_systems=None, _title="25,000 Systems", version=0, scale=500):

        """Plot map  of passiv systems"""

        if number_of_systems is None:
            _data = self.data
        else:
            _data = self.data.sample(number_of_systems)

        _data.sort_values(by="kwp", axis=0, inplace=True)

        res_list = convert_bng(_data.longitude.values.tolist(),
                               _data.latitude.values.tolist())

        fig, ax = plt.subplots(figsize=(6, 12))
        ax = plt.axes(projection=ccrs.OSGB())
        ax.set_extent([1393.0196, 671196.3657, 13494.9764, 1230275.0454], crs=ccrs.OSGB())
        ax.coastlines(resolution='50m')
        ax.gridlines()
        ax.set_title(_title, fontsize=18)
        marker_scale = _data.kwp.values
        sc = ax.scatter(res_list[0], res_list[1], c=marker_scale, s=10,
                   marker="o", cmap="Spectral")
        clb = plt.colorbar(sc)
        clb.ax.set_title("kWp")
        fig_name = "../graphs/passiv_map_{}_{}.png".format(number_of_systems, version)
        fig.savefig(fig_name, bbbbox_inches="tight", dpi=600, transparent=True)
        plt.show()
        return fig


# if __name__ == "__main__":
instance = PlotPassivSystems()
instance.download_passiv_systems()
plot = instance.plot_maps(20000, _title="20k Systems")
plot = instance.plot_maps(10000, "10k Systems")
plot = instance.plot_maps(5000, "5k Systems")
plot = instance.plot_maps(5000, "5k Systems")

plot = instance.plot_maps(1000, "1k Systems", version=0, scale=5000)
plot = instance.plot_maps(1000, "1k Systems", version=1, scale=5000)
plot = instance.plot_maps(1000, "1k Systems", version=2, scale=5000)
plot = instance.plot_maps(1000, "1k Systems", version=3, scale=5000)


plot = instance.plot_maps(50, "50 Systems", version=0, scale=5000)
plot = instance.plot_maps(50, "50 Systems", version=1, scale=5000)
plot = instance.plot_maps(50, "50 Systems", version=2, scale=5000)
plot = instance.plot_maps(50, "50 Systems", version=3, scale=5000)