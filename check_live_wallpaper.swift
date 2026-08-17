import AVFoundation
import CoreMedia
import Foundation

struct WallpaperReport: Encodable {
    let metadataIdentifiers: [String]
    let missingMetadataIdentifiers: [String]
    let wallpaperMetadataPresent: Bool
}

let requiredIdentifiers = [
    "mdta/com.apple.quicktime.live-photo-info",
    "mdta/com.apple.quicktime.live-photo-still-image-transform",
    "mdta/com.apple.quicktime.still-image-time",
]

func metadataIdentifiers(in videoURL: URL) -> [String] {
    let asset = AVURLAsset(url: videoURL)
    let identifiers = asset.tracks(withMediaType: .metadata).flatMap { track in
        track.formatDescriptions.flatMap { format in
            let description = format as! CMFormatDescription
            let values = CMMetadataFormatDescriptionGetIdentifiers(description)
            return (values as! [AVMetadataIdentifier]).map(\.rawValue)
        }
    }

    return Array(Set(identifiers)).sorted()
}

do {
    guard CommandLine.arguments.count == 2 else {
        throw NSError(
            domain: "LivePhotoBatch",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Usage: check_live_wallpaper.swift INPUT.mov"]
        )
    }

    let identifiers = metadataIdentifiers(
        in: URL(fileURLWithPath: CommandLine.arguments[1])
    )
    let missing = requiredIdentifiers.filter { !identifiers.contains($0) }
    let report = WallpaperReport(
        metadataIdentifiers: identifiers,
        missingMetadataIdentifiers: missing,
        wallpaperMetadataPresent: missing.isEmpty
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    FileHandle.standardOutput.write(try encoder.encode(report))
    FileHandle.standardOutput.write(Data("\n".utf8))
} catch {
    FileHandle.standardError.write(Data("error: \(error.localizedDescription)\n".utf8))
    exit(1)
}