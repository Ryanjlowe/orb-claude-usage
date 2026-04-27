// Usage: swiftc get_usage.swift -o get_usage
//        ./get_usage <path-to-image>
//
// Runs Vision OCR on the given image, finds the "Current session" block,
// and prints the usage percentage as a plain integer (e.g. "54").
// Exits 1 with a message on stderr if not found.

import Cocoa
import Vision

guard CommandLine.arguments.count > 1 else {
    fputs("Usage: get_usage <image-path>\n", stderr)
    exit(1)
}

let imagePath = CommandLine.arguments[1]
let imageURL = URL(fileURLWithPath: imagePath)

guard let nsImage = NSImage(contentsOf: imageURL),
      let cgImage = nsImage.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("Error: could not load image at \(imagePath)\n", stderr)
    exit(1)
}

var lines: [String] = []
let semaphore = DispatchSemaphore(value: 0)

let request = VNRecognizeTextRequest { req, _ in
    defer { semaphore.signal() }
    guard let obs = req.results as? [VNRecognizedTextObservation] else { return }
    lines = obs.compactMap { $0.topCandidates(1).first?.string }
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])
semaphore.wait()

// Vision reads left column then right column, so "63% used" may be many lines
// after "Current session". Strategy: once we've seen "Current session", grab
// the first "X% used" that appears anywhere after it in the OCR output.
var seenCurrentSession = false
for line in lines {
    if line.lowercased().contains("current session") {
        seenCurrentSession = true
        continue
    }
    if seenCurrentSession,
       let match = line.range(of: #"(\d{1,3})%\s*used"#, options: .regularExpression) {
        let token = line[match]
        if let numMatch = token.range(of: #"\d{1,3}"#, options: .regularExpression) {
            print(token[numMatch])
            exit(0)
        }
    }
}

fputs("Not found: open Claude → Settings → Usage so the page is visible.\n", stderr)
exit(1)
