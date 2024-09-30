# Developer instuctions

# Installation instructions:
Navigate to the directory where you want to keep the GUI code in terminal, then run:
```
pip install pyqt5 asyncpg numpy pandas
```

```
git clone https://github.com/nkalliney1/wirebonder_gui.git](https://github.com/cmu-hgc-mac/wirebonder_gui.git
```

Go into [conn.py](conn.py) and edit your ```institution_name``` and ```inst_code``` to your respective institution. Change ```host``` to the static IP address of your database computer. Run the code and edit the graphics configuration file.

In [graphics_config.py](graphics_config.py), you can edit the font size of the buttons and other text, as well as the window size to make it fit your computer. If the top of the hexaboard is cut off for the LD full frontside, increase ```add_y_offset```. If the left side of the hexaboard overlaps with the labels for the HD full frontside, increase ```add_x_offset```. Setting it to 40 is a good start.

# Tour of the GUI!
## Home Page
When the code is run, it will open on the homepage.
<img width="1359" alt="image" src="https://github.com/user-attachments/assets/d1977268-8495-47e7-a183-242a229556f1">

### Accessing the wirebonder page
Select the module name prefix from the dropdown. The dropdown will only display the module types produced by your MAC.

<img width="165" alt="image" src="https://github.com/user-attachments/assets/37165df8-b6c3-4883-a2cd-9a96f892b212">

Enter the last four digits of the module name. Click the "load front" or "load back" buttons to show the module's front or back side, respectively.

<img width="237" alt="image" src="https://github.com/user-attachments/assets/686dc13e-5929-4e51-87bb-0c4b69e2ec77">

### Accessing the encapsulation page
Click the encapsulation button to load the encapsulation page.

### Other information

The front page displays a list of all modules that exist in the both wirebonding tables in the database that have <b>not</b> been marked as complete.
"fr" indicates the frontside is incomplete and "bk" indicates the backside is also incomplete.

## Wirebonder
### Front page
The frontside page looks like this.
<img width="1359" alt="image" src="https://github.com/user-attachments/assets/d3c12df0-beff-45d8-8c67-81d39c54a773">
Scroll to the right to see the right side bar buttons or increase your horizontal window sizeif it fits on your computer screen.
<img width="1359" alt="image" src="https://github.com/user-attachments/assets/755bf588-c651-4283-b7fb-2de3eef5f90c">
The page displays a schematic of the frontside of the selected module, with the mousebites as circles outside the edge of the board, the guardrail bonds right inside the edge, and the calibration channels as circles on top of the correct cells. Each cell is numbered, and has a button in the position of its channel. Each channel (mousebite, guardrail, calibration channel, or signal channel) can be left clicked to cycle it between four states concerning wirebonds, represented by colors. The nominal state, blue, represents all three wirebonds were successful. Yellow represents 1 missing bond, orange represents 2 missing bonds, and red represents 3 failed bonds. 

Each channel can be left clicked to cycle between three states concerning grounding. Although mousebites and guardrail bonds can be marked with a grounding flag, these channels are never grounded, so this is not relevant. The nominal state, i.e. a channel without an outline, represents a signal channel. A channel with an outline is marked as "needs to be grounded," and a fully black channel is marked as "grounded."

<img width="330" alt="image" src="https://github.com/user-attachments/assets/17dd3e43-ccaa-415d-82b0-5628477fa167">

On the left, the number of channels in each wirebonding state is displayed.

<img width="156" alt="image" src="https://github.com/user-attachments/assets/2da5356d-9461-4055-a9f8-4b63635bcd64">

The wirebond technician should input their CERN ID and the wedge ID and spool batch in the textboxes on the left, in addition to any comments. On the home page, there is a box that displays modules that need to be revisited. The qualifications for being placed on this list are explained later. However, in order to remove a module from this list, overriding any and all issues with the module, the technician may click the "mark as done" box.

<img width="173" alt="image" src="https://github.com/user-attachments/assets/bf8580e1-9ae8-4916-bf50-ecb7f83554e0">

On the right, the "reset to last saved version" button will reset the page to the last saved version in the database, erasing any changes made since then. The "set to nominal" button resets every button to nominal, i.e. blue and without outline. The "save" button saves the page to the database. Finally, "Help" links to this Readme.

<img width="335" alt="image" src="https://github.com/user-attachments/assets/c132118d-2dfb-4018-9b99-66188141209b">

On the top left, the "Home" button re-opens the home page, updating the list of modules that need to be revisited and auto-saving the page you were just on.

### Back page
The back page displays the mousebites on the back of the module with the cell orientation reversed around the y-axis and the two backside holes for orientation.

<img width="1358" alt="image" src="https://github.com/user-attachments/assets/b7952b91-d112-4939-8e12-2d6d69628dc0">

### Pull testing page
Finally, the pull info page has text boxes for optional pull testing information.

<img width="373" alt="image" src="https://github.com/user-attachments/assets/7b7fe469-ebf5-4838-be6c-daa37dff386d">

This GUI currently has the LD and HD full, LD 5, and LD left and LD right implemented.

### Modules that need to be revisited

When the code is opened, it loops through all modules and checks if a pedestal test has been conducted on it. If so, it compares the list of dead/noisy cells in the pedestal test and the list of dead/noisy cells in the wirebonder GUI. If there is a cell that appears in the pedestal test list but not in the wirebonder list (for example, it was damaged in between wirebonding and testing), it is automatically marked as "needs to be grounded."

Any module with a channel marked as "needs to be grounded" is put on the "needs to be revisited" list unles overwritten by marking it as done.

## Encapsulation
On the encapsulation page, you can add modules to a list by selecting the module name prefix, typing in the number, selecting front or backside encapsulation, and clicking "add." Similarly, a module can be removed from the list if it's already there by clicking "remove." A technician may input their CERN ID and encapsulation information in the textboxes to the right. Clicking "save" will upload that information into the database for every module in the list.

<img width="624" alt="image" src="https://github.com/user-attachments/assets/ea0cbd6f-78e7-4256-a42d-53a9012815ee">

