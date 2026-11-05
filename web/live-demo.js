(() => {
  const video = document.getElementById('product-video');
  const play = document.getElementById('play-explained');
  const captions = document.getElementById('toggle-captions');
  let explanationStarted = false;
  function syncPlayLabel() {
    play.textContent = !explanationStarted ? 'Play with explanation'
      : video.ended ? 'Replay with explanation'
      : video.paused ? 'Resume explanation' : 'Pause explanation';
  }
  play.addEventListener('click', () => {
    if (explanationStarted && !video.paused) { video.pause(); return; }
    if (!explanationStarted || video.ended) video.currentTime = 0;
    explanationStarted = true;
    video.muted = false; video.loop = false;
    video.play().catch(() => { video.controls = true; syncPlayLabel(); });
  });
  ['play', 'pause', 'ended'].forEach(event => video.addEventListener(event, syncPlayLabel));
  video.addEventListener('error', () => {
    document.getElementById('recording-note').textContent = 'The video could not load. Use Download video or inspect the checked file below.';
  });
  captions.addEventListener('click', () => {
    const track = video.textTracks[0];
    if (!track) return;
    const enabled = track.mode !== 'showing';
    track.mode = enabled ? 'showing' : 'disabled';
    captions.setAttribute('aria-pressed', String(enabled));
  });
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { video.autoplay = false; video.pause(); }
})();
