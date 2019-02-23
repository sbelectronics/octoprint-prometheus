# coding=utf-8
from __future__ import absolute_import

import os
from prometheus_client import Gauge, start_http_server
import octoprint.plugin

from .gcodeparser import Gcode_parser

class PrometheusPlugin(octoprint.plugin.StartupPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.ProgressPlugin,
                       octoprint.plugin.EventHandlerPlugin):

        def __init__(self, *args, **kwargs):
            super(PrometheusPlugin, self).__init__(*args, **kwargs)
            self.parser = Gcode_parser()
            self.gauges = {}

        def on_after_startup(self):
            self._logger.info("Starting Prometheus! (port: %s)" % self._settings.get(["prometheus_port"]))
            start_http_server(int(self._settings.get(["prometheus_port"])))
                
        def get_settings_defaults(self):
            return dict(prometheus_port=8000)

        def get_template_configs(self):
            return [
                dict(type="settings", custom_bindings=False)
            ]

        def get_gauge(self, name):
                if name not in self.gauges:
                    self.gauges[name] = Gauge(name, name)
                return self.gauges[name]
        
        def on_print_progress(self, storage, path, progress):
                gauge = self.get_gauge("progress")
                gauge.set(progress)
        
        def on_event(self, event, payload):
                if (event == "ZChange"):
                    gauge = self.get_gauge("zchange")
                    gauge.set(payload["new"])
                if (event == "PrintStarted"):
                    # reset the extrusion counter
                    self.parser.reset()
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
                #self._logger.info("gcodephasehook: cmd=%s gcode=%s, subcode=%s tags=%s args=%s kwargs=%s" % (cmd, gcode, subcode, tags, args, kwargs))
                if self.parser.process_line(cmd):
                    for k in ["x", "y", "z", "e", "speed"]:
                        v = getattr(self.parser, k)
                        if v is not None:
                            gauge = self.get_gauge("movement_" + k)
                            gauge.set(v)
                    gauge = self.get_gauge("extrustion_counter")
                    gauge.set(self.parser.extrusion_counter)
            return None # no change

        def temperatures_handler(self, comm, parsed_temps):
            for (k,v) in parsed_temps.items():
                mapname = {"B": "temperature_bed",
                           "T0": "temperature_tool0",
                           "T1": "temperature_tool1",
                           "T2": "temperature_tool2",
                           "T3": "temperature_tool3"}

                k_actual = mapname.get(k,k) + "_actual"
                gauge = self.get_gauge(k_actual)
                try:
                    gauge.set(v[0])
                except TypeError:
                    pass # not an integer or float

                k_target = mapname.get(k,k) + "_target"
                gauge = self.get_gauge(k_target)
                try:
                    gauge.set(v[1])
                except TypeError:
                    pass # not an integer or float

            return parsed_temps
        

def __plugin_load__():
        plugin = PrometheusPlugin()

        global __plugin_implementation__
        __plugin_implementation__ = plugin

        global __plugin_hooks__
        __plugin_hooks__ = {"octoprint.comm.protocol.temperatures.received": plugin.temperatures_handler,
                            "octoprint.comm.protocol.gcode.sent": plugin.gcodephase_hook}
