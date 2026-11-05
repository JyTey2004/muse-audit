(() => {
  const video = document.getElementById('hero-video');
  const watch = document.getElementById('watch-demo');
  const pause = document.getElementById('pause-preview');
  const status = document.getElementById('film-status');
  const captions = document.getElementById('toggle-captions');
  let narrated = false;
  const update = () => { pause.textContent = video.paused ? 'Play video' : 'Pause video'; pause.setAttribute('aria-pressed', String(video.paused)); };
  pause.addEventListener('click', () => {
    if (video.paused) video.play().catch(() => { video.controls = true; });
    else video.pause();
    update();
  });
  watch.addEventListener('click', () => {
    if (!narrated) {
      narrated = true;
      video.src = 'assets/demo/muse-stardive-demo.mp4';
      video.loop = false;
      video.controls = true;
      video.load();
    } else if (video.ended) video.currentTime = 0;
    video.muted = false;
    captions.hidden = false;
    status.textContent = 'Narrated demo · actual recorded task data · selected checks only';
    document.getElementById('hero-film').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'center' });
    video.play().catch(() => { status.textContent = 'Press Play in the video controls to start the narrated demo.'; });
    update();
  });
  captions.addEventListener('click', () => {
    const track = video.textTracks[0];
    if (!track) return;
    const enabled = track.mode !== 'showing';
    track.mode = enabled ? 'showing' : 'disabled';
    captions.setAttribute('aria-pressed', String(enabled));
  });
  video.addEventListener('play', update);
  video.addEventListener('pause', update);
  video.addEventListener('ended', update);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
    video.autoplay = false; video.pause(); video.controls = true; update();
  }
})();
