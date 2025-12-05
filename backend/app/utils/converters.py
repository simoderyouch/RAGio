import os
import platform

def PPTtoPDF(inputFileName, outputFileName, formatType=32):
    """
    Convert PowerPoint to PDF.
    Note: This is a Windows-only function. On Linux, it will return False.
    """
    if platform.system() != 'Windows':
        print(f"PPT to PDF conversion not available on {platform.system()}: {inputFileName} -> {outputFileName}")
        return False
    
    try:
        import win32com.client
        powerpoint = win32com.client.Dispatch("Powerpoint.Application")
        powerpoint.Visible = False  

        if outputFileName[-3:] != 'pdf':
            outputFileName = outputFileName + ".pdf"
        
        try:
            deck = powerpoint.Presentations.Open(inputFileName)
            deck.SaveAs(outputFileName, formatType)  
            return True
        except Exception as e:
            print("Error:", e)
            return False
        finally:
            if 'deck' in locals():
                deck.Close()
            powerpoint.Quit()
    except ImportError:
        print("win32com not available - PPT to PDF conversion not supported")
        return False