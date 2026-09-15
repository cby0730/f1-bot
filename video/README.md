# F1 bot videos

Isolated [Remotion](https://www.remotion.dev) project for launch films. It does not import `f1_bot`, does not run the Telegram bot, and is not part of the Python package or Docker image.

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
npm run render:proof   # 3s toolchain proof → out/proof.mp4
npm run render:full    # 21s launch film → out/full.mp4
npm run render:short   # 7.5s cut → out/short.mp4
npm run lint
```

`out/` is gitignored. Commit the React source, not the MP4.

The README hero is `docs/demo.gif`, built from `out/full.mp4` (1280×720, 15 fps, infinite loop):

```bash
ffmpeg -y -i out/full.mp4 \
  -vf "fps=15,scale=1280:-1:flags=lanczos,palettegen=max_colors=256:stats_mode=diff" \
  /tmp/palette.png
ffmpeg -y -i out/full.mp4 -i /tmp/palette.png \
  -lavfi "fps=15,scale=1280:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 ../docs/demo.gif
```


## License

Remotion is source-available and free for individuals and teams of up to three people. See [Remotion License](https://www.remotion.dev/docs/license).
