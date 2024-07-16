# wirebonder_gui
Packages required:
```
pip install pyqt5 pandas asyncpg
```
Opens on home page; select module type from dropdown and type in last four digits of module name. The dropdown only shows the module types being produced by your institution. 

Below input, a list of modules that need to be revisited is shown. This includes any module with at least one channel marked "needs to be grounded," or if module pedestal testing has occured, any module that has a cell marked as dead/noisy during the test but has not been marked as grounded in the wirebonder GUI. This marking as "needs to be revisited" can be overriden by checking the "mark as done" box on the front and back pages of the GUI for that module.

Title shows module name.

Front page shows frontside of module, including mousebites outside the edge, guardrail holes inside the edge, and calibration channels. Each channel can be left-clicked to cycle through four flags: blue (all wirebonds successful), yellow (one failed bond), orange (two failed bonds), and red (three failed bonds). Similarly, each channel can be right-clicked to cycle through three flags: no outline (not grounded), black outline (needs to be grounded), and black fill (cell has been grounded).

Back page shows the backside of the module with the mousebites outside the edge. For positioning, the mirror image of the board is shown, in addition to the two holes on the backside. The channels work the same as the front side.

The pull testing page has several text inputs for optional pull testing information.

The upper right corner holds a save button, which saves information from all pages to the database.

Each page has a "reset to last saved version" button, which sets that particular page to the last saved version in the database, erasing all changes made since then.

The front and back pages have a "set to nominal" button, which sets every button to blue and without outline, or all wirebonds successful and not grounded.

A new module can be loaded by returning to the home page. The front, back, and pull pages can't be accessed from the home page without entering a module name. After any changes are saved, returning to the home page will show an updated list of modules that need to be revisited. Returning to the home page autosaves the module that was previously loaded.

When the module information is saved to the database, a list of all non-nominal cells is added to the database under "cell_no" or "mbite_no" for front and back sides, respectively. "bond_count_for_cell/mbite" saves how many successful bonds were made for the cell in the same position in the "cell/mbite_no" list. "bond_count_for_cell" saves the type of bond for each cell on the frontside: "S"- signal, nominal; "N"- needs to be grounded; "G"- grounded. These classifications don't apply to mousebites, so this information is not saved in the backside table. Date and time are autosaved, all other information is from the textboxes.
