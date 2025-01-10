# Documentation

This directory contains the position configuration files for the cells in the hexaboard for the various geometries.

## Legend for `hex_positions.csv` and `backside_mbites_pos.csv`
The hexaboard for `Full` is centered around `(0,0)`. These files contain the `(x,y)` coordinates of the cells in the hexaboard. So a hexagonal cell with a vertex pad and a center pad will have the same coordinates.

## Legend for `pad_to_channel_mapping.csv`
(Ignore ASIC and Channel cols; may be left blank)

Positive pad numbers correspond to a chip+channel combination. 

The negative numbers do not have any physical meaning and are for bookkeeping. Negative numbers smaller than `-12` are guardrail bonds and lie on the perimeter. Other negative numbered pads are mousebites. In the GUI, there are represented with letters that correspond to the `abs(negnum)`. For example, `D` on the GUI is `-4` in the data and code.

`Channeltype == 0` is full hexagon,  
`Channeltype == 1` is outside and circular and has a negative PAD value,   
`Channeltype == 2` is left half-hexagon, (as in the few cells in LD Right),  
`Channeltype == 3` is right half-hexagon

For `Channeltype == 0,2,3`, Channelpos takes on one of seven values from 0 to 6, where   
`Channelpos == 6` implies a circular pad is in the middle of the hexagon.   
`Channelpos == 0,1,2,3,4,5` are representative of the six wedges in the hexagon starting at 90° and moving clockwise.  

![image](https://github.com/user-attachments/assets/44ab495e-b332-4ccd-bc96-10ce1b6aa518)

