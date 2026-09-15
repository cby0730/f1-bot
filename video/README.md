# F1 bot videos

Isolated [Remotion](https://www.remotion.dev) project for launch films. It does not import `f1_bot`, does not run the Telegram bot, and is not part of the Python package or Docker image. Bot architecture and tests live in [`CLAUDE.md`](../CLAUDE.md).

## Why this folder exists

The bot is a Python / `uv` app. Remotion is a Node / React renderer. Keeping every Remotion file under `video/` means pytest, ruff, and the production image stay untouched.

Install Remotion Agent Skills **from this directory** after clone:

```bash
npx remotion skills add
```

Skills land in `video/.agents/skills` (gitignored). They are optional for a local render.

## Commands

```bash
cd video
npm install
npm run dev            # Remotion Studio
npm run compositions   # list compositions
npm run render:full    # 21.7s launch film → out/full.mp4
npm run lint
```

`out/` is gitignored. Commit the React source, not the MP4.

The README hero is `docs/demo.gif`, built from `out/full.mp4` (1920×1080, 30 fps, infinite loop — same as the film):

```bash
ffmpeg -y -i out/full.mp4 \
  -vf "palettegen=max_colors=256:stats_mode=full" \
  /tmp/palette.png
ffmpeg -y -i out/full.mp4 -i /tmp/palette.png \
  -lavfi "paletteuse=dither=floyd_steinberg:diff_mode=rectangle" \
  -loop 0 ../docs/demo.gif
```


## License

Remotion is source-available and free for individuals and teams of up to three people. See [Remotion License](https://www.remotion.dev/docs/license).
