# Spiker's Science Pal's per-app wrappers (Ghostty on the software renderer) come
# before /usr/bin. Spiker's Science Pal's session takes PATH from this login shell.
case ":$PATH:" in
  *:/usr/lib/spikers-science-pal/bin:*) ;;
  *) PATH="/usr/lib/spikers-science-pal/bin:$PATH" ;;
esac
