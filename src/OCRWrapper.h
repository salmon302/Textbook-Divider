
#ifndef TEXTBOOK_DIVIDER_OCRWRAPPER_H
#define TEXTBOOK_DIVIDER_OCRWRAPPER_H

#include <string>
#include <vector>
#include <map>
#include <Python.h>
#include <memory>

class OCRWrapper {
public:
	OCRWrapper();
	~OCRWrapper();
	
	bool initialize(const std::string& lang = "eng", bool enable_gpu = false);
	std::string processImage(const std::string& imagePath);
	std::string processImages(const std::vector<std::string>& imagePaths);
	
	// Enhanced text extraction and feature detection
	std::string extractTextWithFallback(const std::string& pdfPath, int pageNum);
	std::map<std::string, bool> detectFeatures(const std::string& text);
	
	// New OMR capabilities
	struct OMRResult {
		bool success;
		bool hasMusic;
		std::string text;
		std::string musicXML;
		std::string midi;
		std::string error;
	};
	
	OMRResult processPageWithOMR(const std::string& pdfPath, int pageNum);
	bool initializeOMR(const std::string& audiverisPath = "");
	
private:
	void cleanup();
	PyObject* pModule;
	PyObject* pOCRClass;
	PyObject* pOCRInstance;
	PyObject* pOMRClass;
	PyObject* pOMRInstance;
	
	OMRResult parseOMRResult(PyObject* result);
};

#endif // TEXTBOOK_DIVIDER_OCRWRAPPER_H


