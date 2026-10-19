-- Super+P opens SciencePal. Loaded from the user's Hyprland toggles
-- directory, so no Omarchy file is edited.
if type(o) == "table" and type(o.bind) == "function" then
  o.bind("SUPER + P", "SciencePal", { launch = "spikers-science-pal-sciencepal" })
end
