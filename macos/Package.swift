// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "SpikersSciencePalVMHelper",
    platforms: [.macOS("15.0")],
    products: [
        .executable(name: "spikers-vm-helper", targets: ["SpikersSciencePalVMHelper"]),
    ],
    targets: [
        .executableTarget(name: "SpikersSciencePalVMHelper"),
        .testTarget(name: "SpikersSciencePalVMHelperTests", dependencies: ["SpikersSciencePalVMHelper"]),
    ],
    swiftLanguageModes: [.v5]
)
