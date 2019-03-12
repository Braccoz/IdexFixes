# Copyright (c) 2019 Bracco
# The PostProcessingPlugin is released under the terms of the AGPLv3 or higher.
# This script is licensed under the Creative Commons - Attribution - Share Alike (CC BY-SA) terms

from ..Script import Script
from UM.Logger import Logger
from UM.Application import Application
from cura.Settings.ExtruderManager import ExtruderManager

class IdexFixes(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name":"IDEX Fixes",
            "key": "IdexFixes",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "layer_start_fix":
                {
                    "label": "Remove layer start X/Y",
                    "description": "This is a workaround for the Layer Start X/Y bug that enforces it even for Custom FFF printers. Make sure to have both extuders Layer Start X/Y at the same coordinates!",
                    "type": "bool",
                    "default_value": false
                },
                "workingmode":
                {
                    "label": "Working mode",
                    "description": "Select optimization behavior: Full Control Mode or Auto Park Mode. (see Marlin docs for details)",
                    "type": "enum",
                    "options": {"fullcontrol":"Full Control","autopark":"Auto Park"},
                    "default_value": "fullcontrol"
                }
            }
        }"""

        
    def refactor(self,code):
        retval = ""
        switch = ""
        zmove = ""
        retract = ""
        moves = ""
        temps = ""
        section = 0
        countmoves = 0
        for i in range(len(code)):
            if (code[i]).startswith("G") and section == 2:
                if (code[i]).startswith("G1") and "E" in code[i]:
                    retract = code[i] + "\n"
                else:
                    moves += code[i] + "\n"
                    countmoves += 1
                continue            

            elif (code[i]).startswith("G0") and section == 1:
                section = 2
                #this should be the z move, lets take out x and y
                if self.getValue(code[i], 'Z') > 0:
                    ztemps = code[i].split(" ")
                    for zchunks in ztemps:
                        if not zchunks.startswith("X") and not zchunks.startswith("Y"):
                            zmove += zchunks + " "
                    zmove += "\n"
                continue
                
            elif (code[i]).startswith("T") or section == 1:
                section = 1
                switch += code[i] + "\n"
                continue
            else:
                temps += code[i] + "\n"

        if self.getSettingValueByKey("workingmode") == "autopark":    
            retval = zmove + moves + switch + temps + retract
        else:
            retval = zmove + switch + temps + retract + moves.split("\n")[countmoves -1] + "\n"
        return retval
        
        
    def execute(self, data):
        #layer_start_x = Application.getInstance().getGlobalContainerStack().getProperty("layer_start_x", "value")
        layer_start_x = ExtruderManager.getInstance().getActiveExtruderStacks()[0].getProperty("layer_start_x", "value")
        layer_start_y = ExtruderManager.getInstance().getActiveExtruderStacks()[0].getProperty("layer_start_y", "value")
        startfix = False
        if self.getSettingValueByKey("layer_start_fix"):  
            startfix = True
        layercount = 0
        for layer in data:
            lines = layer.split("\n")
            switchlist = []
            newlayer = ""
            worksection = -1
            
            for i in range(len(lines)):
                if layercount > 1: #because the first "layer" block is just machine preparation code
                    if startfix and self.getValue(lines[i], 'G') == 0 and not "Z" in lines[i] and self.getValue(lines[i], 'X') == layer_start_x and self.getValue(lines[i], 'Y') == layer_start_y:
                        if (i+1 < len(lines)) and ";TIME" in lines[i+1]:
                            continue                        

                    if (lines[i]).startswith("T") and worksection < 0:
                       worksection = i                        
                        
                    if worksection >= 0:
                        if lines[i].startswith(";TYPE"):
                            #end of block
                            worksection = -1
                            newlayer += self.refactor(switchlist) + lines[i] + "\n";
                            #Logger.log("e", "done")
                        else:
                            switchlist.append(lines[i])
                        continue                 
 
                newlayer += lines[i] + "\n"

            index = data.index(layer)
            data[index] = newlayer #Override the data of this layer with the modified data
            layercount += 1
        return data
