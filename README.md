# Basics of the GUI

# Installation instructions:

We recommend running this is a separate conda environment or virtual environment and install the required packages. ([See instructions](https://github.com/cmu-hgc-mac/wirebonder_gui/blob/main/README.md#setting-up-environments))

In `python=3.11` with `pip=23.2`, install with `pip`
```
pip install --upgrade pyqt5==5.15.9 asyncpg==0.29.0 numpy==1.25.2 pandas==2.2.2 qasync==0.27.1
```

Navigate to the directory where you want to keep the GUI code in terminal, then clone:
```
git clone https://github.com/cmu-hgc-mac/wirebonder_gui.git
```

Create [config/conn.py](config/conn_example.py) and edit your ```institution_name``` and ```inst_code``` to your respective institution. Change ```host``` to the static IP address of your database computer. Run the code and edit the graphics configuration file.

Create [config/graphics_config.py](config/graphics_config_example.py). Here you can edit the font size of the buttons and other text, as well as the window size to make it fit your computer. If the top of the hexaboard is cut off for the LD full frontside, increase ```add_y_offset```. If the left side of the hexaboard overlaps with the labels for the HD full frontside, increase ```add_x_offset```. Setting it to 40 is a good start.

# Tour of the GUI!
## Home Page
When the code is run, it will open on the homepage.
<img width="1359" alt="image" src="https://github.com/user-attachments/assets/d1977268-8495-47e7-a183-242a229556f1">

### Accessing the wirebonder page
Select the module name prefix from the dropdown. The dropdown will only display the module types produced by your MAC.

<img width="165" alt="image" src="https://github.com/user-attachments/assets/37165df8-b6c3-4883-a2cd-9a96f892b212">

Enter the last four digits of the module name. Click the "load front" or "load back" buttons to show the module's front or back side, respectively.

If you enter the name of a module that doesn't exist yet in the hexaboard or wirebonding tables of the database, you can add it as a blank module to the database (to the module info and wirebonding tables):

<img width="290" alt="image" src="https://github.com/user-attachments/assets/89f54880-88e0-4fff-9687-beb43d92ac48">

Only add modules when strictly necessary! This feature should almost never be used when the workflow is implemented correctly.

### Accessing the encapsulation page
Click the encapsulation button to load the encapsulation page.

### Other information

The front page displays a list of all modules that exist in the both wirebonding tables in the database that have <b>not</b> been marked as complete.
"fr" indicates the frontside is incomplete and "bk" indicates the backside is also incomplete.

Every time you go back to the home page from the encapsulation, front, or back page, the information of that page is automatically saved, except for a few exceptions mentioned below.

## Wirebonder  ([Developer documentation](https://github.com/cmu-hgc-mac/wirebonder_gui/tree/main/geometries#readme))
### Front page
The front page consists of a schematic representation of the board type you have selected, with buttons and text entry on the sidebars.

<img width="1358" alt="image" src="https://github.com/user-attachments/assets/a0edaea2-6586-45c3-8a46-d86d19d14b4f">

Scrolling to the right reveals a few other buttons: 

<img width="342" alt="image" src="https://github.com/user-attachments/assets/b0e75e1e-07aa-419a-a2e8-01a7d55a1cdf">

The schematic representation of the board is composed of hexagons representing each cell, with a button at the corner that corresponds to the location of the wirebonds for that cell. Calibration channels are small circles in the same position they appear on the board. The schematic also represents the mousebites and shield ring bonds as small circles around the edge, in approximately the positions they appear on the board. The button for each cell holds information about the state of the wirebonds of each cell. Left-clicking the cell will cycle it between three states: blue, or 3/3 successful wirebonds; yellow, or 2/3 successful wirebonds; orange, or 1/3 successful wirebonds; or red, unbonded. Right-clicking the cell will cycle it between three states as well: no outline, a signal channel; a black outline, a cell that needs to be grounded; or filled black, a cell that has been grounded.

<img width="369" alt="image" src="https://github.com/user-attachments/assets/73e7ce56-2a0e-4199-b490-d7fbac9064f6">

The right side holds a tally of all states on the board and a key for reading the graphic:

<img width="210" alt="image" src="https://github.com/user-attachments/assets/e5d911ee-8692-4ae6-ad82-3666f939b291">

Information about wirebonding and pull testing (if conducted) may be entered on the textboxes on the right. Note that all pull testing information must be entered separately from wirebonding information, and is not automatically saved for both. The pull testing information will not be saved if the technician's CERN ID is left blank.

<img width="177" alt="image" src="https://github.com/user-attachments/assets/de6226de-95f2-4a6e-92ed-0623f626574f"> <img width="176" alt="image" src="https://github.com/user-attachments/assets/9079859a-b39c-474c-a2b5-fe152fc2f5a1">

The date and time fields are autofilled with the time the page was opened, though this may be changed. The wedge ID and spool batch are also autofilled with the corresponding entries from the last module entered in the database, if the fields are not empty.

The "reset to last saved version" resets all buttons (not text fields) to the last saved version in the database, which does erase any changed made since this particular board was last saved. The "set to nominal" button sets all buttons to 3 successful bonds and signal channels, similarly erasing any changes made since the board was last saved. The "Help" link directs the user to this ReadMe.

<img width="105" alt="image" src="https://github.com/user-attachments/assets/d4d43227-2f31-4c1e-881f-531fe786a24c">

When wirebonding the board has been completed, the user should check the corresponding box, which will remove it from the front page list:

<img width="152" alt="image" src="https://github.com/user-attachments/assets/cd833868-4c94-4814-bb8e-82b110fc9f34">

### Back page

The back page is very similar. It displays a shadow of the frontside as well as the two backside modules holes for orientation, and lacks entries for pull testing. Similarly, when wirebonding has been completed, the user should check the corresponding box.

<img width="1357" alt="image" src="https://github.com/user-attachments/assets/6e707038-82ac-43f4-9f58-6bf7ddaff268">


## Encapsulation
On the encapsulation page, you can add modules to a list by selecting the module name prefix, typing in the number, selecting front or backside encapsulation, and clicking "add." Similarly, a module can be removed from the list if it's already there by clicking "remove."

Information about encapsulation may be entered in the fields to the right; this information will <b>not</b> be saved if any of Cure Start, Cure End, or Encapsulation Time is left empty! The "now" buttons next to the date and time fields will set the date and time to the current time.

The epoxy batch is autofilled from the information of the previous module's, provided it is not empty.

Clicking "save" will upload that information into the database for every module in the list.
<img width="823" alt="image" src="https://github.com/user-attachments/assets/e49d2417-319b-4ba6-9314-e1c5964ed41b">

# Setting up environments
### Conda
We've had success with `conda` on Windows, macOS and Linux. If using `conda`, create an environment `wbgui`:
```
conda create -n wbgui python=3.11 pip=23.2
conda activate wbgui
pip install --upgrade pyqt5==5.15.9 asyncpg==0.29.0 numpy==1.25.2 pandas==2.2.2 qasync==0.27.1
```
Run `conda activate wbgui`. In the environment, run `python wirebonder_gui_database.py`.

### Python venv
```
python3 -m venv wbgui

wbgui\Scripts\activate  # On Windows:
source wbgui/bin/activate # On macOS/Linux

pip install --upgrade pip==23.2
pip install pyqt5==5.15.9 asyncpg==0.29.0 numpy==1.25.2 pandas==2.2.2 qasync==0.27.1
```

Run one of the following to activate the environment for running the GUI.
```
wbgui\Scripts\activate  # On Windows:
source wbgui/bin/activate # On macOS/Linux
```

