// Prints the CGWindowID of the frontmost Claude window, or exits 1 if not found.
// Usage: swiftc get_window_id.swift -o get_window_id && ./get_window_id
import CoreGraphics

guard let wins = CGWindowListCopyWindowInfo(
    [.optionOnScreenOnly, .excludeDesktopElements],
    kCGNullWindowID
) as? [[CFString: Any]] else { exit(1) }

for w in wins {
    if let owner = w[kCGWindowOwnerName] as? String, owner == "Claude",
       let layer = w[kCGWindowLayer] as? Int, layer == 0,
       let wid = w[kCGWindowNumber] as? CGWindowID {
        print(wid)
        exit(0)
    }
}
exit(1)
