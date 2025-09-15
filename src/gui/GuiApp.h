#pragma once

#include <GLFW/glfw3.h>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>
#include <deque>
#include <filesystem>
#include "../FileHandler.h"
#include "../ChapterDetector.h"
#include "../TextProcessor.h"
#include "../OCRWrapper.h"

class GuiApp {
public:
	GuiApp();
	~GuiApp();
	
	void run();
	
private:
	GLFWwindow* window;
	bool setupGLFW();
	void setupImGui();
	void cleanup();
	void renderUI();
	void renderErrorModal();
	
	// UI Components
	void renderSidebar();
	void renderMainContent();
	void renderChapterPreview();
	void renderSettings();
	void renderMetricsPanel();
	void renderOutputExplorer();
	
	// Application state
	std::string inputPath;
	std::string outputPath;
	std::atomic<bool> processing{false};
	std::atomic<float> progress{0.0f};
	std::vector<std::string> chapterList;
	std::string statusMessage;
	bool enableOCR;
	std::string selectedLanguage;
	bool enableGPU;
	bool showError{false};
	std::string errorMessage;
	bool depsChecked{false};
	bool depsOK{true};
	
	// New state variables
	int currentChapter;
	std::string previewContent;
	bool showSettings;
	bool showMetrics{true};
	bool showExplorer{true};
	std::string searchFilter;
	
	// Background processing
	std::thread worker;
	std::atomic<bool> cancelRequested{false};
	std::mutex logMutex;
	std::deque<std::string> logLines;
	std::chrono::steady_clock::time_point runStartTime;
	
	// OCR preset & params
	enum class OCRPreset { Accuracy, Balanced, Speed, SpeedMax, PSM3, PSM6, FastPreprocess };
	OCRPreset ocrPreset{OCRPreset::Balanced};
	int ocrPSM{3};
	int ocrConfThreshold{30};
	bool ocrFullMode{false};
	
	// Chapter detection settings
	struct {
		float minChapterLength;
		int minTitleLength;
		bool detectSubchapters;
		float confidenceThreshold;
	} detectionSettings;
	
	// Core components
	FileHandler fileHandler;
	ChapterDetector chapterDetector;
	TextProcessor textProcessor;
	std::unique_ptr<OCRWrapper> ocrProcessor;
	
	// Processing APIs
	void startProcessing();
	void processThread();
	void processWithOCR();
	void processWithoutOCR();
	void updateChapterPreview();
	bool checkDependencies();
	void appendLog(const std::string& line);
	void applyPreset();
	bool applyPresetFromConfig(const std::string& path);
	std::string getPresetConfigPath() const;
	void refreshChapterListFromOutput();
	
	// Metrics
	struct PageMetric { int index{0}; double avgConf{0.0}; int charCount{0}; double ms{0.0}; };
	std::vector<PageMetric> pageMetrics;
};