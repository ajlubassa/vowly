# Vowly Stage 7.2 — sidebar fix

This patch fixes the Free plan box covering lower navigation options.

What changed:
- Sidebar uses a proper vertical flex layout.
- Navigation scrolls independently when the screen is short.
- Free plan box stays at the bottom and no longer overlaps links.
- Plan box becomes more compact on shorter screens.

Deploy:
1. Upload all Stage 7.2 files to the root of your existing `ajlubassa/vowly` GitHub repository.
2. Replace the current files.
3. Commit:
   `Vowly Stage 7.2 sidebar fix`
4. Keep Railway `web-volume` mounted at `/data`.
5. Wait for Railway to show Online.
6. Open Vowly and press Ctrl + F5 once.
