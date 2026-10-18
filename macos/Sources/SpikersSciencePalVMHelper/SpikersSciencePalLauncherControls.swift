import AppKit

enum SpikersSciencePalControlStyle {
    case primary
    case secondary
    case danger
}

final class SpikersSciencePalActionButton: NSButton {
    private let spikersStyle: SpikersSciencePalControlStyle
    private var displayTitle: String
    private var hoverTrackingArea: NSTrackingArea?
    private var isPointerInside = false
    private var isPointerDown = false

    init(
        title: String,
        style: SpikersSciencePalControlStyle,
        target: AnyObject?,
        action: Selector?
    ) {
        displayTitle = title.uppercased()
        spikersStyle = style
        super.init(frame: .zero)
        self.target = target
        self.action = action
        setAccessibilityLabel(title)
        configure()
    }

    required init?(coder: NSCoder) {
        nil
    }

    override var isEnabled: Bool {
        didSet { refreshAppearance() }
    }

    func updateTitle(_ title: String) {
        displayTitle = title.uppercased()
        setAccessibilityLabel(title)
        refreshAppearance()
    }

    override var intrinsicContentSize: NSSize {
        let titleSize = attributedTitle.size()
        return NSSize(width: ceil(titleSize.width) + 32, height: ceil(titleSize.height) + 16)
    }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let hoverTrackingArea {
            removeTrackingArea(hoverTrackingArea)
        }
        let trackingArea = NSTrackingArea(
            rect: .zero,
            options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(trackingArea)
        hoverTrackingArea = trackingArea
    }

    override func mouseEntered(with event: NSEvent) {
        isPointerInside = true
        refreshAppearance()
    }

    override func mouseExited(with event: NSEvent) {
        isPointerInside = false
        refreshAppearance()
    }

    override func mouseDown(with event: NSEvent) {
        guard isEnabled else {
            super.mouseDown(with: event)
            return
        }
        isPointerDown = true
        refreshAppearance()
        super.mouseDown(with: event)
        isPointerDown = false
        refreshAppearance()
    }

    override func resetCursorRects() {
        super.resetCursorRects()
        addCursorRect(bounds, cursor: isEnabled ? .pointingHand : .arrow)
    }

    private func configure() {
        setButtonType(.momentaryPushIn)
        isBordered = false
        focusRingType = .none
        wantsLayer = true
        layer?.cornerRadius = 6
        layer?.borderWidth = 1
        translatesAutoresizingMaskIntoConstraints = false
        refreshAppearance()
    }

    private func refreshAppearance() {
        guard let layer else { return }

        let background: NSColor
        let foreground: NSColor
        let border: NSColor

        if !isEnabled {
            background = SpikersSciencePalStartMenuTheme.lighterBackground.withAlphaComponent(0.45)
            foreground = SpikersSciencePalStartMenuTheme.muted.withAlphaComponent(0.48)
            border = SpikersSciencePalStartMenuTheme.lighterBackground.withAlphaComponent(0.7)
        } else {
            switch spikersStyle {
            case .primary:
                background = isPointerDown
                    ? SpikersSciencePalStartMenuTheme.cyan
                    : (isPointerInside ? SpikersSciencePalStartMenuTheme.hover : SpikersSciencePalStartMenuTheme.accent)
                foreground = SpikersSciencePalStartMenuTheme.background
                border = background
            case .secondary:
                background = isPointerDown
                    ? SpikersSciencePalStartMenuTheme.lighterBackground
                    : SpikersSciencePalStartMenuTheme.darkBackground
                foreground = isPointerInside
                    ? SpikersSciencePalStartMenuTheme.hover
                    : SpikersSciencePalStartMenuTheme.foreground
                border = isPointerInside
                    ? SpikersSciencePalStartMenuTheme.accent
                    : SpikersSciencePalStartMenuTheme.lighterBackground
            case .danger:
                background = isPointerDown || isPointerInside
                    ? SpikersSciencePalStartMenuTheme.danger
                    : SpikersSciencePalStartMenuTheme.darkBackground
                foreground = isPointerDown || isPointerInside
                    ? SpikersSciencePalStartMenuTheme.background
                    : SpikersSciencePalStartMenuTheme.danger
                border = isPointerDown || isPointerInside
                    ? SpikersSciencePalStartMenuTheme.danger
                    : SpikersSciencePalStartMenuTheme.lighterBackground
            }
        }

        layer.backgroundColor = background.cgColor
        layer.borderColor = border.cgColor
        layer.shadowOpacity = spikersStyle == .primary && isEnabled ? 0.22 : 0
        layer.shadowColor = NSColor.black.cgColor
        layer.shadowOffset = NSSize(width: 0, height: -2)
        layer.shadowRadius = 0
        attributedTitle = NSAttributedString(
            string: displayTitle,
            attributes: [
                .font: NSFont.monospacedSystemFont(ofSize: 11, weight: .bold),
                .foregroundColor: foreground,
                .kern: 0.35,
            ]
        )
        invalidateIntrinsicContentSize()
    }
}

final class SpikersSciencePalToggleButton: NSButton {
    private var hoverTrackingArea: NSTrackingArea?
    private var isPointerInside = false

    init(isOn: Bool, target: AnyObject?, action: Selector?) {
        super.init(frame: .zero)
        self.target = target
        self.action = action
        setButtonType(.toggle)
        state = isOn ? .on : .off
        setAccessibilityLabel("Immersive mode")
        configure()
    }

    required init?(coder: NSCoder) {
        nil
    }

    override var state: NSControl.StateValue {
        didSet { refreshAppearance() }
    }

    override var isEnabled: Bool {
        didSet { refreshAppearance() }
    }

    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        if let hoverTrackingArea {
            removeTrackingArea(hoverTrackingArea)
        }
        let trackingArea = NSTrackingArea(
            rect: .zero,
            options: [.mouseEnteredAndExited, .activeInKeyWindow, .inVisibleRect],
            owner: self,
            userInfo: nil
        )
        addTrackingArea(trackingArea)
        hoverTrackingArea = trackingArea
    }

    override func mouseEntered(with event: NSEvent) {
        isPointerInside = true
        refreshAppearance()
    }

    override func mouseExited(with event: NSEvent) {
        isPointerInside = false
        refreshAppearance()
    }

    override func resetCursorRects() {
        super.resetCursorRects()
        addCursorRect(bounds, cursor: isEnabled ? .pointingHand : .arrow)
    }

    func refreshAppearance() {
        guard let layer else { return }
        let isOn = state == .on
        let background: NSColor
        let foreground: NSColor
        let border: NSColor

        if !isEnabled {
            background = SpikersSciencePalStartMenuTheme.lighterBackground.withAlphaComponent(0.4)
            foreground = SpikersSciencePalStartMenuTheme.muted.withAlphaComponent(0.48)
            border = SpikersSciencePalStartMenuTheme.lighterBackground
        } else if isOn {
            background = isPointerInside ? SpikersSciencePalStartMenuTheme.hover : SpikersSciencePalStartMenuTheme.accent
            foreground = SpikersSciencePalStartMenuTheme.background
            border = background
        } else {
            background = SpikersSciencePalStartMenuTheme.darkBackground
            foreground = isPointerInside ? SpikersSciencePalStartMenuTheme.hover : SpikersSciencePalStartMenuTheme.foreground
            border = isPointerInside ? SpikersSciencePalStartMenuTheme.accent : SpikersSciencePalStartMenuTheme.lighterBackground
        }

        layer.backgroundColor = background.cgColor
        layer.borderColor = border.cgColor
        attributedTitle = NSAttributedString(
            string: isOn ? "[ ON ]" : "[ OFF ]",
            attributes: [
                .font: NSFont.monospacedSystemFont(ofSize: 10, weight: .bold),
                .foregroundColor: foreground,
                .kern: 0.25,
            ]
        )
        setAccessibilityValue(isOn ? "On" : "Off")
    }

    private func configure() {
        isBordered = false
        focusRingType = .none
        wantsLayer = true
        layer?.cornerRadius = 6
        layer?.borderWidth = 1
        translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            widthAnchor.constraint(equalToConstant: 66),
            heightAnchor.constraint(equalToConstant: 30),
        ])
        refreshAppearance()
    }
}
