
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
	
	// Initialize OCR processor with language, GPU toggle, and key params
	bool initialize(const std::string& lang = "eng", bool enable_gpu = false, int psm = 3, int conf_threshold = 30);
	std::string processImage(const std::string& imagePath);
	std::string processImages(const std::vector<std::string>& imagePaths);

	// Process a single image and return metrics (text, avg confidence, char count, elapsed ms)
	struct OCRResultWithMetrics {
		std::string text;
		double avg_conf{0.0};
		int char_count{0};
		double elapsed_ms{0.0};
		bool success{false};
	};
	OCRResultWithMetrics processImageWithMetrics(const std::string& imagePath, bool fullMode);

	// Retrieve processor stats (cache, memory, workers, etc.)
	std::map<std::string, std::string> getStats();

	// Apply a JSON config file directly to the Python OCRProcessor (returns applied keys/values as strings)
	std::map<std::string, std::string> applyConfigFile(const std::string& jsonPath);
	
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


