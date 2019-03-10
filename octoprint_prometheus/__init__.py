# coding=utf-8

""" Octoprint-Prometheus
    Scott Baker, http://www.smbaker.com/

    This is an Octoprint plugin that exposes a Prometheus client endpoint, allowing printer statistics to be
    collected by Prometheus and view in Grafana.

    Development notes:
       # Sourcing the oprint environment on the pi for development.
       source ~/oprint/bin/activate

       # Find octoprint logs here
       tail -f /home/pi/.octoprint/logs/octoprint.log
"""

from __future__ import absolute_import

from threading import Timer
from prometheus_client import Counter, Enum, Gauge, Info, start_http_server
import octoprint.plugin

from .gcodeparser import Gcode_parser


class PrometheusPlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.ProgressPlugin,
                       octoprint.plugin.EventHandlerPlugin):

        DESCRIPTIONS = {"temperature_bed_actual": "Actual Temperature in Celsius of Bed",
                        "temperature_bed__target": "Target Temperature in Celsius of Bed",
                        "temperature_tool0_actual": "Actual Temperature in Celsius of Extruder Hot End",
                        "temperature_tool0__target": "Target Temperature in Celsius of Extruder Hot End",
                        "movement_x": "Movement of X axis from G0 or G1 gcode",
                        "movement_y": "Movement of Y axis from G0 or G1 gcode",
                        "movement_z": "Movement of Z axis from G0 or G1 gcode",
                        "movement_e": "Movement of Extruder from G0 or G1 gcode",
                        "movement_speed": "Speed setting from G0 or G1 gcode",
                        "extrusion_print": "Filament extruded this print",
                        "extrusion_total": "Filament extruded total",
                        "progress": "Progress percentage of print",
                        "printing": "1 if printing, 0 otherwise",
                        "print": "Filename information about print",
                        }

        def __init__(self, *args, **kwargs):
            super(PrometheusPlugin, self).__init__(*args, **kwargs)
            self.parser = Gcode_parser()
            self.gauges = {}  # holds gauges, counters, infos, and enums
            self.last_extrusion_counter = 0
            self.completion_timer = None

            self.gauges["printer_state"] = Enum("printer_state",
                                                "State of printer",
                                                states=["init", "printing", "done", "failed", "cancelled", "idle"])
            self.gauges["printer_state"].state("init")

            self.init_gauge("progress")
            self.init_gauge("extrusion_print")
            self.init_gauge("printing")
            self.init_gauge("zchange")
            self.init_gauge("movement_x")
            self.init_gauge("movement_y")
            self.init_gauge("movement_z")
            self.init_gauge("movement_e")
            self.init_gauge("movement_speed")
            self.init_gauge("temperature_bed_actual")
            self.init_gauge("temperature_bed_target")
            self.init_gauge("temperature_tool0_actual")
            self.init_gauge("temperature_tool0_target")
            self.init_gauge("temperature_tool1_actual")
            self.init_gauge("temperature_tool1_target")
            self.init_gauge("temperature_tool2_actual")
            self.init_gauge("temperature_tool2_target")
            self.init_gauge("temperature_tool3_actual")
            self.init_gauge("temperature_tool3_target")

            self.init_counter("extrusion_total")

            self.init_info("print")

        def on_after_startup(self):
            self._logger.info("Starting Prometheus! (port: %s)" % self._settings.get(["prometheus_port"]))
            start_http_server(int(self._settings.get(["prometheus_port"])))
                
        def get_settings_defaults(self):
            return dict(prometheus_port=8000)

        def get_template_configs(self):
            return [
                dict(type="settings", custom_bindings=False)
            ]

        def init_gauge(self, name):
            self.gauges[name] = Gauge(name, self.DESCRIPTIONS.get(name, name))

        def init_counter(self, name):
            self.gauges[name] = Counter(name, self.DESCRIPTIONS.get(name, name))

        def init_info(self, name):
            self.gauges[name] = Info(name, self.DESCRIPTIONS.get(name, name))

        def get_gauge(self, name):
            return self.gauges[name]

        def on_print_progress(self, storage, path, progress):
                gauge = self.get_gauge("progress")
                gauge.set(progress)

        def print_complete_callback(self):
            self.get_gauge("printer_state").state("idle")
            self.get_gauge("progress").set(0)
            self.get_gauge("extrusion_print").set(0)
            self.get_gauge("print").info({})   # This doesn't actually cause it to reset...
            self.completion_timer = None

        def print_complete(self, reason):
            self.get_gauge("printer_state").state(reason)
            self.get_gauge("printing").set(0)  # TODO: may be redundant with printer_state

            # In 30 seconds, reset all the progress variables back to 0
            # At a default 10 second interval, this gives us plenty of room for Prometheus to capture the 100%
            # complete gauge.

            # TODO: Is this really a good idea?

            self.completion_timer = Timer(30, self.print_complete_callback)
            self.completion_timer.start()

        def on_event(self, event, payload):
                if event == "ZChange":
                    # TODO: This doesn't seem useful...
                    gauge = self.get_gauge("zchange")
                    gauge.set(payload["new"])
                elif event == "PrintStarted":
                    # If there's a completion timer running, kill it.
                    if self.completion_timer:
                        self.completion_timer.cancel()
                        self.completion_timer = None

                    # reset the extrusion counter
                    self.parser.reset()
                    self.last_extrusion_counter = 0
                    self.get_gauge("printing").set(1)  # TODO: may be redundant with printer_state
                    self.get_gauge("printer_state").state("printing")
                    self.get_gauge("print").info({"name": payload.get("name", ""),
                                                  "path": payload.get("path", ""),
                                                  "origin": payload.get("origin", "")})
                elif event == "PrintFailed":
                    self.print_complete("failed")
                elif event == "PrintDone":
                    self.print_complete("done")
                elif event == "PrintCancelled":
                    self.print_complete("cancelled")

                """
                # This was my first attempt at measuring positions and extrusions. 
                # Didn't work the way I expected.
                # Went with gcodephase_hook and counting extrusion gcode instead.
                if (event == "PositionUpdate"):
                    for (k,v) in payload.items():
                        if k in ["x", "y", "z", "e"]:
                            k = "position_" + k
                            gauge = self.get_gauge(k)
                            gauge.set(v)
                """

        def gcodephase_hook(self, comm_instance, phase, cmd, cmd_type, gcode, subcode=None, tags=None, *args, **kwargs):
            if phase == "sent":
                if self.parser.process_line(cmd):
                    for k in ["x", "y", "z", "e", "speed"]:
                        v = getattr(self.parser, k)
                        if v is not None:
                            gauge = self.get_gauge("movement_" + k)
                            gauge.set(v)

                    # extrusion_print is modeled as a gauge so we can reset it after every print
                    gauge = self.get_gauge("extrusion_print")
                    gauge.set(self.parser.extrusion_counter)

                    if self.parser.extrusion_counter > self.last_extrusion_counter:
                        # extrusion_total is monotonically increasing for the lifetime of the plugin
                        counter = self.get_gauge("extrusion_total")
                        counter.inc(self.parser.extrusion_counter - self.last_extrusion_counter)
                        self.last_extrusion_counter = self.parser.extrusion_counter

            return None  # no change

        def temperatures_handler(self, comm, parsed_temps):
            for (k, v) in parsed_temps.items():
                mapname = {"B": "temperature_bed",
                           "T0": "temperature_tool0",
                           "T1": "temperature_tool1",
                           "T2": "temperature_tool2",
                           "T3": "temperature_tool3"}

                # We only support four tools. If someone runs into a printer with more tools, please
                # let me know...
                if k not in mapname:
                    continue

                k_actual = mapname.get(k, k) + "_actual"
                gauge = self.get_gauge(k_actual)
                try:
                    gauge.set(v[0])
                except TypeError:
                    pass  # not an integer or float

                k_target = mapname.get(k, k) + "_target"
                gauge = self.get_gauge(k_target)
                try:
                    gauge.set(v[1])
                except TypeError:
                    pass  # not an integer or float

            return parsed_temps
        

def __plugin_load__():
        plugin = PrometheusPlugin()

        global __plugin_implementation__
        __plugin_implementation__ = plugin

        global __plugin_hooks__
        __plugin_hooks__ = {"octoprint.comm.protocol.temperatures.received": plugin.temperatures_handler,
                            "octoprint.comm.protocol.gcode.sent": plugin.gcodephase_hook}
