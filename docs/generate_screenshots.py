import sys
import os
import time
from PySide6 import QtWidgets, QtCore, QtGui
import pypdfium2 as pdfium

# Add current directory to path so we can import main
sys.path.append(os.getcwd())

from main import PdfAnnotator

def create_dummy_pdf(path):
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(595, 842) # A4
    pdf.save(path)
    print(f"Created dummy PDF at {path}")
    return os.path.abspath(path)

def capture_window(window, filename):
    pixmap = window.grab()
    pixmap.save(filename)
    print(f"Saved screenshot to {filename}")

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Ensure directory exists
    os.makedirs("docs/images", exist_ok=True)
    
    # Create a dummy PDF to load
    dummy_pdf_path = os.path.join("docs", "sample.pdf")
    create_dummy_pdf(dummy_pdf_path)

    # Initialize Main Window
    window = PdfAnnotator()
    window.resize(1280, 800)
    window.show()
    
    # Give it a moment to initialize
    app.processEvents()
    time.sleep(1)
    
    # Simulate Opening the PDF
    # We call the internal method or slot that handles file opening if accessible,
    # or we set the attributes directly if needed. 
    # Looking at main.py, let's try to find a method to open file.
    # Assuming 'open_pdf(path)' or similar exists, or we can invoke the logic.
    # If not, we might rely on the window being empty and just capture that.
    # But user wants "program execution capture", so loading a file is better.
    
    # Based on main.py analysis in previous turn, we didn't see the exact open method in the view_file output (lines 1-800).
    # We saw 'load_model' in Worker, 'publish_project', etc.
    # Let's inspect 'main.py' more to find the 'file open' method title.
    # But for now, let's try to just capture the main UI. 
    # If we can't easily open a PDF programmatically without more analysis, we will capture the empty state first.
    
    # Capture Main Window
    capture_window(window, "docs/images/01_mainwindow.png")

    # Capture a menu or dialog if possible (simulated)
    # For example, New Project Dialog
    from ui.dialogs import NewProjectDialog
    dlg = NewProjectDialog(window)
    dlg.show()
    app.processEvents()
    time.sleep(0.5)
    capture_window(dlg, "docs/images/02_newproject_dialog.png")
    dlg.close()

    # Clean up
    window.close()

if __name__ == "__main__":
    main()
