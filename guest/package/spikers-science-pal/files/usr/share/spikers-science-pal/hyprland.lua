-- Spiker's Science Pal's Hyprland additions for the Mac VM. Loaded from the user's
-- Spiker's Science Pal toggles directory (~/.local/state/omarchy/toggles/hypr), which
-- Spiker's Science Pal reads after the user's own configuration on every reload, so no
-- Spiker's Science Pal or user file is edited. The spikers-science-pal package owns this file.

local function host_option(expected)
  local file = io.open("/run/spikers-science-pal/cmdline", "r")
  if not file then
    return false
  end
  local options = file:read("*a") or ""
  file:close()
  for option in options:gmatch("%S+") do
    if option == expected then
      return true
    end
  end
  return false
end

if host_option("spikers.qemu_virgl=1") then
  -- QEMU's Cocoa display draws the Mac cursor outside the guest scanout for
  -- immediate motion, so the guest cursor stays hidden. The window's backing
  -- size and refresh rate arrive through Virtio GPU EDID; the sync helper
  -- applies them at start and again after every configuration reload.
  hl.config({ cursor = { invisible = true } })
  o.exec_on_start("/usr/bin/spikers-native-display-sync")
  hl.on("config.reloaded", function()
    -- Spiker's Science Pal hides the pointer while a session starts and then restores the
    -- cursor settings it captured (default/hypr/startup-cursor.lua), which
    -- can predate this file. Keep the guest cursor hidden in that capture,
    -- and once more after its 15-second reveal fallback.
    if type(spikers_startup_cursor) == "table" and type(spikers_startup_cursor.config) == "table" then
      spikers_startup_cursor.config.invisible = true
    end
    hl.timer(function()
      hl.config({ cursor = { invisible = true } })
    end, { timeout = 16000, type = "oneshot" })
    hl.exec_cmd("/usr/bin/spikers-native-display-sync --once")
  end)
  -- Spiker's Science Pal's screensaver shows the cursor again as it exits, right before
  -- its window closes. Hide it whenever a window goes away; it is already
  -- hidden, so for any other window this changes nothing. When the window is
  -- closed first, the screensaver's own reveal comes after this, so hide it
  -- once more a moment later.
  hl.on("window.destroy", function()
    hl.config({ cursor = { invisible = true } })
    hl.timer(function()
      hl.config({ cursor = { invisible = true } })
    end, { timeout = 1000, type = "oneshot" })
  end)
end

pcall(dofile, "/usr/share/spikers-science-pal/pinch-input.lua")
pcall(dofile, "/usr/share/spikers-science-pal/apple-keyboard-input.lua")
