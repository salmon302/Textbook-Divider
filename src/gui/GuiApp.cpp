#include "GuiApp.h"
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <nfd.hpp>
#include <stdexcept>
#include <cstdlib>
#include <filesystem>
#include <sstream>
#include <algorithm>
#include <fstream>

GuiApp::GuiApp() : window(nullptr),
	enableOCR(false), selectedLanguage("eng"), enableGPU(false),
	currentChapter(-1), showSettings(false) {
	// Initialize detection settings
	detectionSettings = {
		1000.0f,  // minChapterLength
		10,       // minTitleLength
		true,     // detectSubchapters
		0.75f     // confidenceThreshold
	};
	if (!setupGLFW()) {
		throw std::runtime_error("Failed to initialize GLFW");
	}
	setupImGui();
	
	if (NFD::Init() != NFD_OKAY) {
		throw std::runtime_error("Failed to initialize NFD");
	}

	// Check external dependencies (once)
	depsChecked = true;
	depsOK = checkDependencies();
	
	ocrProcessor = std::make_unique<OCRWrapper>();
	if (!ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold)) {
		showError = true;
		errorMessage = "Failed to initialize OCR. Ensure Python, pytesseract, and dependencies are available.";
	}
	
	statusMessage = "Ready";
}

GuiApp::~GuiApp() {
	NFD::Quit();
	cleanup();
}

bool GuiApp::setupGLFW() {
	if (!glfwInit()) return false;
	
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	window = glfwCreateWindow(800, 600, "Textbook Divider", nullptr, nullptr);
	
	if (!window) {
		glfwTerminate();
		return false;
	}
	
	glfwMakeContextCurrent(window);
	glfwSwapInterval(1);
	return true;
}

void GuiApp::setupImGui() {
	IMGUI_CHECKVERSION();
	ImGui::CreateContext();
	ImGui_ImplGlfw_InitForOpenGL(window, true);
	ImGui_ImplOpenGL3_Init("#version 130");
	ImGui::StyleColorsDark();
}

void GuiApp::cleanup() {
	if (worker.joinable()) {
		cancelRequested = true;
		worker.join();
	}
	ImGui_ImplOpenGL3_Shutdown();
	ImGui_ImplGlfw_Shutdown();
	ImGui::DestroyContext();
	if (window) {
		glfwDestroyWindow(window);
	}
	glfwTerminate();
}

void GuiApp::renderUI() {
	// Main window using the entire viewport
	ImGui::SetNextWindowPos(ImVec2(0, 0));
	ImGui::SetNextWindowSize(ImGui::GetIO().DisplaySize);
	ImGui::Begin("Textbook Divider", nullptr, 
		ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse);

	// Left panel (controls)
	ImGui::BeginChild("LeftPanel", ImVec2(280, -1), true);
	renderSidebar();
	ImGui::EndChild();

	ImGui::SameLine();

	// Right panel split into top main content and bottom metrics
	ImGui::BeginChild("RightPanelAll", ImVec2(0, -1), false);
	{
		// Top: main content and explorer side-by-side
		ImGui::BeginChild("RightTop", ImVec2(0, showMetrics ? ImGui::GetWindowHeight() * 0.65f : -1), true);
		renderMainContent();
		ImGui::EndChild();
		if (showMetrics) {
			ImGui::Separator();
			ImGui::BeginChild("RightBottomMetrics", ImVec2(0, 0), true);
			renderMetricsPanel();
			ImGui::EndChild();
		}
	}
	ImGui::EndChild();

	// Settings window (floating)
	if (showSettings)
		renderSettings();

	// Error modal overlay
	renderErrorModal();

	ImGui::End();
}

void GuiApp::renderSidebar() {
	if (ImGui::Button("Select Input File")) {

		NFD::UniquePath outPath;
		nfdfilteritem_t filterItem[2] = {
			{ "PDF", "pdf" },
			{ "Text", "txt" }
		};
		nfdresult_t result = NFD::OpenDialog(outPath, filterItem, 2);
		if (result == NFD_OKAY) {
			inputPath = outPath.get();
		}
	}
	ImGui::SameLine();
	ImGui::Text("%s", inputPath.empty() ? "No file selected" : inputPath.c_str());

	if (ImGui::Button("Select Output Directory")) {
		NFD::UniquePath outPath;
		nfdresult_t result = NFD::PickFolder(outPath);
		if (result == NFD_OKAY) {
			outputPath = outPath.get();
		}
	}
	ImGui::SameLine();
	ImGui::Text("%s", outputPath.empty() ? "No directory selected" : outputPath.c_str());

	// Add OCR settings
	if (ImGui::CollapsingHeader("OCR Settings", ImGuiTreeNodeFlags_DefaultOpen)) {
		ImGui::Checkbox("Enable OCR", &enableOCR);
		
		if (enableOCR) {
			const char* languages[] = { "eng", "fra", "deu", "spa", "ita" };
			const char* langNames[] = { "English", "French", "German", "Spanish", "Italian" };
			
			if (ImGui::BeginCombo("Language", selectedLanguage.c_str())) {
				for (int i = 0; i < IM_ARRAYSIZE(languages); i++) {
					bool isSelected = (selectedLanguage == languages[i]);
					if (ImGui::Selectable(langNames[i], isSelected)) {
						selectedLanguage = languages[i];
						ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
					}
					if (isSelected) {
						ImGui::SetItemDefaultFocus();
					}
				}
				ImGui::EndCombo();
			}
			
			if (ImGui::Checkbox("Enable GPU", &enableGPU)) {
				ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
			}

			// Presets
			const char* presetNames[] = { "Accuracy", "Balanced", "Speed", "Speed Max", "PSM 3", "PSM 6", "Fast Preprocess" };
			int presetIdx = static_cast<int>(ocrPreset);
			if (ImGui::Combo("Preset", &presetIdx, presetNames, IM_ARRAYSIZE(presetNames))) {
				ocrPreset = static_cast<OCRPreset>(presetIdx);
				applyPreset();
				ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
				// Apply full preset config to Python if present
				std::string cfg = getPresetConfigPath();
				if (!cfg.empty()) {
					ocrProcessor->applyConfigFile(cfg);
				}
			}
			ImGui::SliderInt("PSM", &ocrPSM, 0, 13);
			ImGui::SliderInt("Word conf thr", &ocrConfThreshold, 0, 100);
			ImGui::Checkbox("Full preprocess", &ocrFullMode);

			// Load custom config file and apply to Python OCR
			if (ImGui::Button("Load config file…")) {
				NFD::UniquePath jsonPath;
				nfdfilteritem_t filterItem[1] = { { "JSON", "json" } };
				if (NFD::OpenDialog(jsonPath, filterItem, 1) == NFD_OKAY) {
					// First call to read applied values for UI reflection
					auto applied = ocrProcessor->applyConfigFile(jsonPath.get());
					// Reflect key fields back into UI if present
					try {
						if (applied.count("ocr_psm")) {
							ocrPSM = std::stoi(applied["ocr_psm"]);
						}
						if (applied.count("ocr_word_conf_threshold")) {
							ocrConfThreshold = std::stoi(applied["ocr_word_conf_threshold"]);
						}
						if (applied.count("fast_preprocess")) {
							// fast_preprocess=true => prefer fast path (so uncheck full preprocess)
							std::string v = applied["fast_preprocess"];
							std::transform(v.begin(), v.end(), v.begin(), ::tolower);
							bool fast = (v == "true" || v == "1");
							ocrFullMode = !fast;
						}
						// Re-init OCR with new core params, then re-apply full config to persist other settings
						ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
						ocrProcessor->applyConfigFile(jsonPath.get());
					} catch (...) {
						// ignore UI reflect errors
					}
				}
			}
		}
	}

	if (!inputPath.empty() && !outputPath.empty()) {
		if (!processing && ImGui::Button("Process Textbook")) {
			if (!depsOK) {
				showError = true;
				errorMessage = "Missing dependencies. Please install Poppler (pdftoppm) and ensure it is in PATH.";
				return;
			}
			startProcessing();
		}
		if (processing && ImGui::Button("Cancel")) {
			cancelRequested = true;
		}
	}

	ImGui::ProgressBar(progress.load());
	ImGui::Text("%s", statusMessage.c_str());

	// Live log tail
	if (ImGui::CollapsingHeader("Log")) {
		std::lock_guard<std::mutex> lk(logMutex);
		for (const auto& ln : logLines) {
			ImGui::TextWrapped("%s", ln.c_str());
		}
	}
}


void GuiApp::renderMainContent() {
	// Chapter list on the left side of the right panel
	ImGui::BeginChild("ChapterList", ImVec2(250, 0), true);
	if (ImGui::Button("Refresh Output")) {
		refreshChapterListFromOutput();
	}
	{
		static char buf[256] = {0};
		if (!searchFilter.empty() && strlen(buf) == 0) {
			strncpy(buf, searchFilter.c_str(), sizeof(buf)-1);
		}
		if (ImGui::InputTextWithHint("##search", "Filter chapters...", buf, sizeof(buf))) {
			searchFilter = std::string(buf);
		}
	}

	for (size_t i = 0; i < chapterList.size(); i++) {
		if (!searchFilter.empty()) {
			if (chapterList[i].find(searchFilter) == std::string::npos) continue;
		}
		if (ImGui::Selectable(chapterList[i].c_str(), currentChapter == (int)i)) {
			currentChapter = i;
			updateChapterPreview();
		}
	}
	ImGui::EndChild();
	
	ImGui::SameLine();
	
	// Chapter preview on the right with explorer toggle
	ImGui::BeginChild("Preview", ImVec2(0, 0), true);
	ImGui::Checkbox("Show metrics", &showMetrics); ImGui::SameLine();
	ImGui::Checkbox("Show explorer", &showExplorer);
	if (showExplorer) {
		ImGui::Separator();
		renderOutputExplorer();
		ImGui::Separator();
	}
	if (currentChapter >= 0 && currentChapter < chapterList.size()) {
		ImGui::TextWrapped("%s", previewContent.c_str());
	} else {
		ImGui::TextWrapped("Select a chapter to preview its content");
	}
	ImGui::EndChild();
}


void GuiApp::renderSettings() {
	ImGui::SetNextWindowSize(ImVec2(400, 400), ImGuiCond_FirstUseEver);
	ImGui::Begin("Settings", &showSettings, ImGuiWindowFlags_NoCollapse);
	
	if (ImGui::CollapsingHeader("OCR Settings")) {
		ImGui::Checkbox("Enable OCR", &enableOCR);
		if (enableOCR) {
			const char* languages[] = { "eng", "fra", "deu", "spa", "ita" };
			const char* langNames[] = { "English", "French", "German", "Spanish", "Italian" };
			
			if (ImGui::BeginCombo("Language", selectedLanguage.c_str())) {
				for (int i = 0; i < IM_ARRAYSIZE(languages); i++) {
					bool isSelected = (selectedLanguage == languages[i]);
					if (ImGui::Selectable(langNames[i], isSelected)) {
						selectedLanguage = languages[i];
						ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
					}
					if (isSelected) {
						ImGui::SetItemDefaultFocus();
					}
				}
				ImGui::EndCombo();
			}
			
			if (ImGui::Checkbox("Enable GPU", &enableGPU)) {
				ocrProcessor->initialize(selectedLanguage, enableGPU, ocrPSM, ocrConfThreshold);
			}
		}
	}
	
	if (ImGui::CollapsingHeader("Chapter Detection")) {
		ImGui::SliderFloat("Min Chapter Length", &detectionSettings.minChapterLength, 100.0f, 5000.0f);
		ImGui::SliderInt("Min Title Length", &detectionSettings.minTitleLength, 5, 50);
		ImGui::Checkbox("Detect Subchapters", &detectionSettings.detectSubchapters);
		ImGui::SliderFloat("Confidence Threshold", &detectionSettings.confidenceThreshold, 0.0f, 1.0f);
	}
	
	ImGui::End();
}

void GuiApp::updateChapterPreview() {
	if (currentChapter >= 0 && currentChapter < chapterList.size()) {
		// Load chapter content from file
		std::string chapterPath = outputPath + "/chapter_" + std::to_string(currentChapter + 1) + ".txt";
		previewContent = fileHandler.readFile(chapterPath);
	}
}

void GuiApp::run() {
	while (!glfwWindowShouldClose(window)) {
		glfwPollEvents();
		
		ImGui_ImplOpenGL3_NewFrame();
		ImGui_ImplGlfw_NewFrame();
		ImGui::NewFrame();
		
		renderUI();
		
		ImGui::Render();
		int display_w, display_h;
		glfwGetFramebufferSize(window, &display_w, &display_h);
		glViewport(0, 0, display_w, display_h);
		glClear(GL_COLOR_BUFFER_BIT);
		ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
		
		glfwSwapBuffers(window);
	}
}

void GuiApp::processWithOCR() {
	std::string content;
	if (fileHandler.isImageFile(inputPath)) {
		auto res = ocrProcessor->processImageWithMetrics(inputPath, ocrFullMode);
		content = res.text;
		pageMetrics.clear();
		pageMetrics.push_back({1, res.avgConf, res.char_count, res.elapsed_ms});
	} else if (fileHandler.isPDFFile(inputPath)) {
		auto images = fileHandler.extractPDFImages(inputPath);
		content.clear();
		pageMetrics.clear();
		const size_t total = images.size();
		for (size_t i = 0; i < images.size(); ++i) {
			if (cancelRequested) break;
			auto start = std::chrono::high_resolution_clock::now();
			auto res = ocrProcessor->processImageWithMetrics(images[i], ocrFullMode);
			auto end = std::chrono::high_resolution_clock::now();
			res.elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();
			pageMetrics.push_back({(int)(i+1), res.avg_conf, res.char_count, res.elapsed_ms});
			if (!res.text.empty()) {
				content += res.text + "\n\n";
			}
			progress = static_cast<float>((i + 1) / (double)total);
			std::ostringstream oss; oss << "Page " << (i+1) << "/" << total << ": conf=" << res.avg_conf << ", chars=" << res.char_count;
			appendLog(oss.str());
		}
	} else {
		throw std::runtime_error("File format not supported for OCR");
	}
	
	progress = std::max(progress.load(), 0.3f);
	
	content = textProcessor.cleanText(content);
	content = textProcessor.formatText(content);
	progress = std::max(progress.load(), 0.6f);
	
	auto chapters = chapterDetector.detectChapters(content);
	if (chapters.empty()) {
		throw std::runtime_error("No chapters detected");
	}
	
	for (const auto& chapter : chapters) {
		if (!fileHandler.saveChapter(chapter.content, outputPath, chapter.number)) {
			throw std::runtime_error("Failed to save chapter " + std::to_string(chapter.number));
		}
		chapterList.push_back("Chapter " + std::to_string(chapter.number) + ": " + chapter.title);
	}
	
	progress = 1.0f;
	statusMessage = "Processing complete!";
}

bool GuiApp::checkDependencies() {
	// Check for Poppler's pdftoppm (used by FileHandler::extractPDFImages)
#ifdef _WIN32
	const char* cmd = "where pdftoppm >nul 2>nul";
#else
	const char* cmd = "which pdftoppm >/dev/null 2>&1";
#endif
	int code = system(cmd);
	return code == 0;
}

void GuiApp::renderErrorModal() {
	if (showError) {
		ImGui::OpenPopup("Error");
	}
	if (ImGui::BeginPopupModal("Error", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
		ImGui::TextWrapped("%s", errorMessage.c_str());
		ImGui::Separator();
		if (ImGui::Button("OK", ImVec2(120, 0))) {
			showError = false;
			ImGui::CloseCurrentPopup();
		}
		ImGui::EndPopup();
	}
}

void GuiApp::startProcessing() {
	if (processing) return;
	processing = true;
	cancelRequested = false;
	progress = 0.0f;
	chapterList.clear();
	previewContent.clear();
	pageMetrics.clear();
	logLines.clear();
	runStartTime = std::chrono::steady_clock::now();
	worker = std::thread(&GuiApp::processThread, this);
}

void GuiApp::processThread() {
	try {
		if (enableOCR) {
			processWithOCR();
		} else {
			processWithoutOCR();
		}
	} catch (const std::exception& e) {
		statusMessage = std::string("Error: ") + e.what();
		showError = true;
		errorMessage = statusMessage;
	}
	processing = false;
}

void GuiApp::processWithoutOCR() {
	if (!fileHandler.openFile(inputPath)) {
		throw std::runtime_error("Could not open input file");
	}
	std::string content = fileHandler.readContent();
	progress = 0.3f;
	content = textProcessor.cleanText(content);
	content = textProcessor.formatText(content);
	progress = 0.6f;
	auto chapters = chapterDetector.detectChapters(content);
	if (chapters.empty()) {
		throw std::runtime_error("No chapters detected");
	}
	for (const auto& chapter : chapters) {
		if (!fileHandler.saveChapter(chapter.content, outputPath, chapter.number)) {
			throw std::runtime_error("Failed to save chapter " + std::to_string(chapter.number));
		}
		chapterList.push_back("Chapter " + std::to_string(chapter.number) + ": " + chapter.title);
	}
	progress = 1.0f;
	statusMessage = "Processing complete!";
}

void GuiApp::appendLog(const std::string& line) {
	std::lock_guard<std::mutex> lk(logMutex);
	logLines.push_back(line);
	if (logLines.size() > 200) logLines.pop_front();
}

void GuiApp::applyPreset() {
	switch (ocrPreset) {
		case OCRPreset::Accuracy:
			ocrPSM = 11; ocrConfThreshold = 40; ocrFullMode = true; break;
		case OCRPreset::Balanced:
			ocrPSM = 6; ocrConfThreshold = 30; ocrFullMode = false; break;
		case OCRPreset::Speed:
			ocrPSM = 6; ocrConfThreshold = 26; ocrFullMode = false; break;
		case OCRPreset::SpeedMax:
			ocrPSM = 6; ocrConfThreshold = 24; ocrFullMode = false; break;
		case OCRPreset::PSM3:
			ocrPSM = 3; break;
		case OCRPreset::PSM6:
			ocrPSM = 6; break;
		case OCRPreset::FastPreprocess:
			ocrPSM = 11; ocrConfThreshold = 28; ocrFullMode = false; break;
	}
	// Attempt to override from config JSON if present
	std::string cfg = getPresetConfigPath();
	if (!cfg.empty()) {
		applyPresetFromConfig(cfg);
	}
}

std::string GuiApp::getPresetConfigPath() const {
	namespace fs = std::filesystem;
	fs::path base = fs::path("configs");
	switch (ocrPreset) {
		case OCRPreset::Accuracy: return (base/"ocr_dev.json").string();
		case OCRPreset::Balanced: return (base/"ocr_dev.json").string();
		case OCRPreset::Speed: return (base/"ocr_dev_speed.json").string();
		case OCRPreset::SpeedMax: return (base/"ocr_dev_speed_max.json").string();
		case OCRPreset::PSM3: return (base/"ocr_dev_speed_psm3.json").string();
		case OCRPreset::PSM6: return (base/"ocr_dev_speed_psm6.json").string();
		case OCRPreset::FastPreprocess: return (base/"ocr_dev_speed_fast.json").string();
		default: return "";
	}
}

// Minimal JSON key reader (psm, thresholds) without external deps
bool GuiApp::applyPresetFromConfig(const std::string& path) {
	try {
		std::ifstream f(path);
		if (!f.is_open()) return false;
		std::string s((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
		auto findInt = [&](const std::string& key, int& out){
			auto pos = s.find("\""+key+"\""); if (pos==std::string::npos) return false;
			pos = s.find(":", pos); if (pos==std::string::npos) return false;
			size_t i = s.find_first_of("-0123456789", pos);
			if (i==std::string::npos) return false;
			size_t j=i; while (j<s.size() && (isdigit((unsigned char)s[j]) || s[j]=='-')) j++;
			try { out = std::stoi(s.substr(i, j-i)); return true; } catch(...) { return false; }
		};
		auto findBool = [&](const std::string& key, bool& out){
			auto pos = s.find("\""+key+"\""); if (pos==std::string::npos) return false;
			pos = s.find(":", pos); if (pos==std::string::npos) return false;
			size_t i = s.find_first_not_of(" \t\r\n", pos+1);
			if (i==std::string::npos) return false;
			if (s.compare(i, 4, "true")==0) { out = true; return true; }
			if (s.compare(i, 5, "false")==0) { out = false; return true; }
			return false;
		};
		// Map fields
		int psmVal; if (findInt("ocr_psm", psmVal)) ocrPSM = psmVal;
		int thr; if (findInt("ocr_word_conf_threshold", thr)) ocrConfThreshold = thr;
		bool fastPre = false; if (findBool("fast_preprocess", fastPre)) ocrFullMode = !fastPre; // invert: fast_preprocess=false => full
		return true;
	} catch (...) { return false; }
}

void GuiApp::renderMetricsPanel() {
	// Aggregate metrics
	double avgConfAll = 0.0; int n=0; int totalChars=0; double totalMs=0.0;
	for (const auto& m : pageMetrics) { avgConfAll += m.avgConf; totalChars += m.charCount; totalMs += m.ms; n++; }
	if (n>0) avgConfAll /= n;
	std::string elapsed;
	auto now = std::chrono::steady_clock::now();
	auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now - runStartTime).count();
	std::ostringstream oss; oss << (ms/1000.0) << "s"; elapsed = oss.str();
	ImGui::Text("Avg conf: %.2f | Total chars: %d | Pages: %d | Elapsed: %s", avgConfAll, totalChars, n, elapsed.c_str());
	if (ImGui::BeginTable("metrics", 4, ImGuiTableFlags_Borders | ImGuiTableFlags_RowBg | ImGuiTableFlags_Resizable)) {
		ImGui::TableSetupColumn("Page");
		ImGui::TableSetupColumn("Avg conf");
		ImGui::TableSetupColumn("Chars");
		ImGui::TableSetupColumn("ms");
		ImGui::TableHeadersRow();
		for (const auto& m : pageMetrics) {
			ImGui::TableNextRow();
			ImGui::TableSetColumnIndex(0); ImGui::Text("%d", m.index);
			ImGui::TableSetColumnIndex(1); ImGui::Text("%.2f", m.avgConf);
			ImGui::TableSetColumnIndex(2); ImGui::Text("%d", m.charCount);
			ImGui::TableSetColumnIndex(3); ImGui::Text("%.1f", m.ms);
		}
		ImGui::EndTable();
	}
	// Python-side stats
	auto stats = ocrProcessor->getStats();
	for (const auto& kv : stats) {
		ImGui::Text("%s: %s", kv.first.c_str(), kv.second.c_str());
	}
}

void GuiApp::renderOutputExplorer() {
	if (outputPath.empty()) return;
	namespace fs = std::filesystem;
	try {
		if (!fs::exists(outputPath)) return;
		for (auto& p : fs::directory_iterator(outputPath)) {
			if (!p.is_regular_file()) continue;
			auto path = p.path().string();
			if (path.size() >= 4 && path.substr(path.size()-4) == ".txt") {
				if (ImGui::Selectable(path.c_str(), false)) {
					previewContent = fileHandler.readFile(path);
				}
			}
		}
	} catch (...) {
	}
}

void GuiApp::refreshChapterListFromOutput() {
	chapterList.clear();
	namespace fs = std::filesystem;
	try {
		if (!fs::exists(outputPath)) return;
		std::vector<std::pair<int,std::string>> temp;
		for (auto& p : fs::directory_iterator(outputPath)) {
			if (!p.is_regular_file()) continue;
			auto filename = p.path().filename().string();
			if (filename.rfind("chapter_", 0) == 0 && filename.find(".txt") != std::string::npos) {
				try {
					auto numStr = filename.substr(8, filename.find('.')-8);
					int num = std::stoi(numStr);
					temp.push_back({num, filename});
				} catch (...) {}
			}
		}
		std::sort(temp.begin(), temp.end(), [](auto&a, auto&b){return a.first<b.first;});
		for (auto& it : temp) {
			chapterList.push_back("Chapter " + std::to_string(it.first));
		}
	} catch (...) {
	}
}