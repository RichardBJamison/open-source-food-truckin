Open Source Food Truckin' - Program v1.3.0-beta
===============================================
October 2026 public beta · Free · GPL-3.0-or-later
Sister program to Open Source Barware.

WHAT YOU DOWNLOADED
-------------------
A self-contained food truck inventory program. It runs on YOUR computer in
Chrome at http://127.0.0.1:5053/ - no subscription, no cloud account needed.

Voice walk of the truck, sections you define, daily / weekly / monthly
counts, invoices, purchase orders, POS import, plate costing and load lists
all work without AI. Optional AI (in setup or Settings) only reads invoice
photos and suggests shelves - you can always type numbers yourself.

LICENSE: GNU GPL v3 or later. See LICENSE.txt in this folder.


MAC INSTALL (5 minutes)
-----------------------
1. Double-click the downloaded .zip once to unzip it.
2. Open the folder "open-source-food-truckin-program".
3. Double-click START-HERE-MAC.html (opens in your browser, shows every step
   with pictures-in-words). Or follow step 4 here.
4. Double-click Install.command.
   macOS may say it "can't be opened" / "Apple could not verify". That is
   expected for free software without an Apple certificate.
   FIX (macOS 15+): click Done, open System Settings > Privacy & Security,
   scroll down, click "Open Anyway", then double-click Install.command again.
   FIX (macOS 14 and older): Right-click Install.command > Open > Open.
   Terminal option:
     cd ~/Downloads/open-source-food-truckin-program
     xattr -cr .
     chmod +x Install.command
     ./Install.command
5. Asked to install "command line developer tools"? Click Install, wait,
   then run Install.command again (that is your Mac installing Python).
6. Wait for "Setup complete!" - your browser opens to the program.
7. Bookmark http://127.0.0.1:5053/ in Chrome. That bookmark IS the software.

The program installs to:  ~/osft-program
It starts automatically when you log in.


WINDOWS INSTALL (5-10 minutes)
------------------------------
1. Right-click the .zip > Extract All.
2. Open the folder "open-source-food-truckin-program".
3. Double-click Install.bat  (do not double-click install.ps1)
4. If SmartScreen says "Windows protected your PC": More info > Run anyway
5. If Python is missing the installer opens https://www.python.org/downloads/
   Check "Add python.exe to PATH" during setup, then run Install.bat again.
6. Wait for "Setup complete!" - your browser opens to the program.
7. Bookmark http://127.0.0.1:5053/ in Chrome or Edge.

The program installs to:  %USERPROFILE%\osft-program
It starts automatically when you log in (Startup folder shortcut
"Open Source Food Truckin").


LINUX / BY HAND
---------------
Use the Mac zip:  ./install.sh   (runs in this folder; Ctrl+C stops it)


FIRST RUN
---------
The welcome screen walks the truck with you: name your sections (cab,
reach-in, line cooler, dry storage...), speak or type what is in each one,
upload invoices or invoice photos in the same spot, then Reconcile shows
what it registered and asks where invoice-only items go. Edit anything
right on the Reconcile step. AI is optional - skip it and use the full
program now; add it later in Settings.

Voice counting works in Chrome, Edge and Safari (not Firefox). Typing
always works.


DAILY USE
---------
Open your bookmark: http://127.0.0.1:5053/

Manual start:
  Mac:     double-click Start.command (in ~/osft-program)
  Windows: double-click Start.bat (in %USERPROFILE%\osft-program)
Stop:
  Mac:     Stop.command
  Windows: Stop.bat


VERIFY IT WORKS
---------------
Open http://127.0.0.1:5053/ - you should see the OSFT home screen.
If not, check the log:
  Mac:     ~/osft-program/data/osft_server.log
  Windows: %USERPROFILE%\osft-program\data\osft_server.log


CLEAN UP YOUR DOWNLOADS FOLDER (after install succeeds)
-------------------------------------------------------
The live program is in ~/osft-program (Mac) or %USERPROFILE%\osft-program
(Windows). Safe to delete afterwards:
  - the .zip in Downloads (osft-1.3.0-beta-mac.zip / -win.zip)
  - the unzipped "open-source-food-truckin-program" folder
Keep: everything in osft-program and your bookmark.


UNINSTALL
---------
1. Run Stop.command (Mac) or Stop.bat (Windows)
2. Mac: launchctl bootout gui/$(id -u) com.osfoodtrucking.program
        then delete ~/Library/LaunchAgents/com.osfoodtrucking.program.plist
3. Windows: delete "Open Source Food Truckin" from your Startup folder
4. Delete the install folder:
   Mac:     rm -rf ~/osft-program
   Windows: delete %USERPROFILE%\osft-program


UPDATES
-------
Check https://osfoodtrucking.com/download/ for new builds. Re-run
Install.command or Install.bat over your install - your data/ is kept.


SUPPORT & SOURCE
----------------
Website:  https://osfoodtrucking.com
Source:   https://github.com/RichardBJamison/open-source-food-truckin
Email:    me@richardbjamison.com


===============================================
EN ESPANOL - INSTALACION RAPIDA
===============================================
MAC
1. Haz doble clic en el .zip para descomprimirlo.
2. Abre la carpeta "open-source-food-truckin-program".
3. Abre START-HERE-MAC.html (instrucciones paso a paso, tambien en espanol).
4. Doble clic en Install.command. Si el Mac lo bloquea: Ajustes del Sistema >
   Privacidad y seguridad > "Abrir igualmente", y vuelve a hacer doble clic.
5. Si pide "herramientas de desarrollo", haz clic en Instalar y repite.
6. Se abre el programa en http://127.0.0.1:5053/ - guardalo en favoritos.

WINDOWS
1. Clic derecho en el .zip > Extraer todo.
2. Abre la carpeta "open-source-food-truckin-program".
3. Doble clic en Install.bat.
4. Si aparece "Windows protegio su PC": Mas informacion > Ejecutar de todas formas.
5. Sin Python: instalalo desde python.org marcando "Add python.exe to PATH"
   y vuelve a ejecutar Install.bat.
6. Se abre el programa en http://127.0.0.1:5053/ - guardalo en favoritos.

Tus datos quedan en tu computadora. Para actualizar, ejecuta el nuevo
instalador: tus datos se conservan.
