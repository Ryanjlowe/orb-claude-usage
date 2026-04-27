// Captures the Claude desktop window, runs Vision OCR, and prints the
// "Current session" usage percentage as a plain integer (e.g. "54").
//
// Compile:
//   swiftc get_usage.swift -o get_usage
//
// On first run macOS will prompt for Screen Recording permission.
// Grant it in: System Settings → Privacy & Security → Screen Recording

import Cocoa
import Vision
import ScreenCaptureKit

// ── helpers ──────────────────────────────────────────────────────────────────

func fail(_ msg: String) -> Never { fputs(msg + "\n", stderr); exit(1) }

func parsePercent(from lines: [String]) -> Int? {
    var seenSession = false
    for line in lines {
        if line.lowercased().contains("current session") { seenSession = true; continue }
        if seenSession,
           let m = line.range(of: #"(\d{1,3})%\s*used"#, options: .regularExpression),
           let n = line[m].range(of: #"\d{1,3}"#, options: .regularExpression) {
            return Int(line[m][n])
        }
    }
    return nil
}

func ocrLines(from image: CGImage) -> [String] {
    var out: [String] = []
    let sem = DispatchSemaphore(value: 0)
    let req = VNRecognizeTextRequest { r, _ in
        out = (r.results as? [VNRecognizedTextObservation] ?? [])
            .compactMap { $0.topCandidates(1).first?.string }
        sem.signal()
    }
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    try? VNImageRequestHandler(cgImage: image, options: [:]).perform([req])
    sem.wait()
    return out
}

// ── entry point ───────────────────────────────────────────────────────────────

// NSApplication.shared initialises the Cocoa/CGS stack required by SCKit
let app = NSApplication.shared
app.setActivationPolicy(.prohibited)

let sem = DispatchSemaphore(value: 0)

Task {
    defer { sem.signal() }

    // 1. Get shareable content (triggers permission prompt on first run)
    let content: SCShareableContent
    do {
        content = try await SCShareableContent.excludingDesktopWindows(false,
                                                                       onScreenWindowsOnly: true)
    } catch {
        fail("Screen Recording permission denied.\n" +
             "Grant it in System Settings → Privacy & Security → Screen Recording,\n" +
             "then re-run this command.")
    }

    // 2. Find Claude window
    guard let win = content.windows.first(where: {
        $0.owningApplication?.applicationName == "Claude" && $0.isOnScreen
    }) else {
        fail("Claude window not found — is the app running with Settings → Usage visible?")
    }

    // 3. Capture
    let filter = SCContentFilter(desktopIndependentWindow: win)
    let cfg = SCStreamConfiguration()
    cfg.width   = Int(win.frame.width  * 2)
    cfg.height  = Int(win.frame.height * 2)
    cfg.showsCursor = false

    let image: CGImage
    do {
        image = try await SCScreenshotManager.captureImage(contentFilter: filter,
                                                           configuration: cfg)
    } catch {
        fail("Capture failed: \(error.localizedDescription)")
    }

    // 4. OCR → parse
    let lines = ocrLines(from: image)
    guard let pct = parsePercent(from: lines) else {
        fail("Could not find usage % — navigate to Claude Settings → Usage.")
    }
    print(pct)
    exit(0)
}

sem.wait()
