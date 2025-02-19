#include <podofo/podofo.h>
#include <iostream>
#include <string>

int main() {
	try {
		PoDoFo::PdfMemDocument document;
		PoDoFo::PdfPainter painter;
		PoDoFo::PdfFont* pFont;

		// Create pages
		for (int i = 0; i < 4; ++i) {
			PoDoFo::PdfPage* pPage = document.CreatePage(PoDoFo::PdfPage::CreateStandardPageSize(PoDoFo::ePdfPageSize_A4));
			painter.SetPage(pPage);
			
			pFont = document.CreateFont("Helvetica");
			pFont->SetFontSize(12.0);
			painter.SetFont(pFont);

			std::string chapterTitle = "Chapter " + std::to_string(i + 1);
			std::string content = "This is test content for " + chapterTitle;

			painter.DrawText(50, pPage->GetPageSize().GetHeight() - 50, chapterTitle.c_str());
			painter.DrawText(50, pPage->GetPageSize().GetHeight() - 80, content.c_str());
			
			painter.FinishPage();
		}

		document.Write("sample_books/sample.pdf");
		return 0;
	} catch (const PoDoFo::PdfError& e) {
		std::cerr << "Error: " << e.what() << std::endl;
		return 1;
	}
}