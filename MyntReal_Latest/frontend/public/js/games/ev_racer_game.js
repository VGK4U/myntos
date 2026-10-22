/**
 * Game G: EV Racer 3D — Cyber Highway & Energy Dash (DC Protocol Oct 2026)
 * High-performance pseudo-3D perspective racer featuring an Electric Supercar,
 * regenerative braking, turbo energy boost, battery management, solar orbs,
 * dynamic traffic overtaking, and seamless touch + keyboard responsive controls.
 */

class EVRacerGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    // Player EV Car State
    this.playerX = 0;       // -1.0 (Left edge) to +1.0 (Right edge)
    this.targetX = 0;
    this.speedMode = 'NORMAL';
    this.modeBaseSpeed = 190;
    this.modeMaxSpeed = 290;
    this.modeBoostSpeed = 380;
    this.baseSpeed = 190;
    this.speed = 190;       // km/h
    this.maxSpeed = 290;
    this.boostSpeed = 380;
    this.brakeSpeed = 75;
    this.isBoosting = false;
    this.isBraking = false;
    this.levelUpBannerTimer = 0;
    this.levelUpText = '';

    // Battery & Energy Mechanics
    this.battery = 100.0;   // 0.0 to 100.0%
    this.batteryMax = 100.0;
    this.totalDistance = 0; // In meters
    this.batteryPacksCollected = 0;

    // World & Road Geometry
    this.roadZ = 0;
    this.roadCurvature = 0;
    this.targetCurvature = 0;
    this.curveTimer = 0;

    // Traffic & Collectibles Arrays
    this.traffic = [];
    this.items = [];
    this.particles = [];
    this.speedLines = [];

    // Screen Shake & Visual FX
    this.shakeDuration = 0;
    this.shakeIntensity = 0;

    // Loop & Control States
    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;
    this.lastTimestamp = 0;

    // Input Tracking
    this.keys = { left: false, right: false, up: false, down: false };

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const w = Math.min(parentWidth - 16, 520);
    const h = Math.min(window.innerHeight * 0.46, 480);

    this.canvas.width = w;
    this.canvas.height = h;

    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    // 1. Keyboard Controls (Laptop & Desktop)
    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      if (['ArrowLeft', 'KeyA'].includes(e.code)) {
        this.keys.left = true;
      } else if (['ArrowRight', 'KeyD'].includes(e.code)) {
        this.keys.right = true;
      } else if (['ArrowUp', 'KeyW', 'Space'].includes(e.code)) {
        this.keys.up = true;
      } else if (['ArrowDown', 'KeyS'].includes(e.code)) {
        this.keys.down = true;
      }
    });

    window.addEventListener('keyup', (e) => {
      if (['ArrowLeft', 'KeyA'].includes(e.code)) {
        this.keys.left = false;
      } else if (['ArrowRight', 'KeyD'].includes(e.code)) {
        this.keys.right = false;
      } else if (['ArrowUp', 'KeyW', 'Space'].includes(e.code)) {
        this.keys.up = false;
      } else if (['ArrowDown', 'KeyS'].includes(e.code)) {
        this.keys.down = false;
      }
    });

    // 2. Direct Pointer / Touch Drag on Canvas (Mobile & Touch Laptops)
    let isPointerDown = false;
    const handlePointerMove = (clientX) => {
      if (!this.isRunning || this.isPaused) return;
      const rect = this.canvas.getBoundingClientRect();
      const relX = (clientX - rect.left) / rect.width; // 0 to 1
      this.targetX = Math.max(-0.88, Math.min(0.88, (relX - 0.5) * 2.1));
    };

    this.canvas.addEventListener('pointerdown', (e) => {
      isPointerDown = true;
      handlePointerMove(e.clientX);
    });

    window.addEventListener('pointermove', (e) => {
      if (isPointerDown) handlePointerMove(e.clientX);
    });

    window.addEventListener('pointerup', () => {
      isPointerDown = false;
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  // Touch / Mobile D-Pad Triggers (Invoked from HTML buttons)
  steerLeft(active = true) {
    this.keys.left = active;
  }

  steerRight(active = true) {
    this.keys.right = active;
  }

  triggerBoost(active = true) {
    this.keys.up = active;
  }

  triggerBrake(active = true) {
    this.keys.down = active;
  }

  setSpeedMode(mode) {
    this.speedMode = mode;
    if (mode === 'SLOW') {
      this.modeBaseSpeed = 140;
      this.modeMaxSpeed = 220;
      this.modeBoostSpeed = 300;
    } else if (mode === 'FAST') {
      this.modeBaseSpeed = 260;
      this.modeMaxSpeed = 380;
      this.modeBoostSpeed = 460;
    } else if (mode === 'TURBO') {
      this.modeBaseSpeed = 340;
      this.modeMaxSpeed = 480;
      this.modeBoostSpeed = 560;
    } else { // NORMAL
      this.modeBaseSpeed = 190;
      this.modeMaxSpeed = 290;
      this.modeBoostSpeed = 380;
    }
    const currentLevel = (this.framework && this.framework.level) ? this.framework.level : 1;
    const levelSpeedBonus = (currentLevel - 1) * 20;
    this.baseSpeed = this.modeBaseSpeed + levelSpeedBonus;
    this.maxSpeed = this.modeMaxSpeed + levelSpeedBonus;
    this.boostSpeed = this.modeBoostSpeed + levelSpeedBonus;

    // Immediately update current speed if running
    if (this.isRunning && this.speed < this.baseSpeed) {
      this.speed = this.baseSpeed;
    }
  }

  // ── LIFECYCLE ──
  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this.lastTimestamp = performance.now();
    this._initWorld();
    this._loop();
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this.lastTimestamp = performance.now();
    this._loop();
  }

  reset() {
    this.isRunning = false;
    this.isPaused = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    this.playerX = 0;
    this.targetX = 0;
    const currentLevel = (this.framework && this.framework.level) ? this.framework.level : 1;
    const levelSpeedBonus = (currentLevel - 1) * 20;
    this.baseSpeed = (this.modeBaseSpeed || 190) + levelSpeedBonus;
    this.maxSpeed = (this.modeMaxSpeed || 290) + levelSpeedBonus;
    this.boostSpeed = (this.modeBoostSpeed || 380) + levelSpeedBonus;
    this.speed = this.baseSpeed;
    this.battery = 100.0;
    this.levelUpBannerTimer = 0;
    this.levelUpText = '';
    this.totalDistance = 0;
    this.batteryPacksCollected = 0;
    this.roadZ = 0;
    this.roadCurvature = 0;
    this.targetCurvature = 0;
    this.curveTimer = 0;
    this.shakeDuration = 0;

    this.traffic = [];
    this.items = [];
    this.particles = [];
    this.speedLines = [];
    this.keys = { left: false, right: false, up: false, down: false };
  }

  _initWorld() {
    // Generate initial traffic vehicles
    for (let i = 0; i < 4; i++) {
      this._spawnTraffic(600 + i * 450);
    }
    // Generate initial energy items
    for (let i = 0; i < 5; i++) {
      this._spawnItem(300 + i * 320);
    }
  }

  _spawnTraffic(distZ) {
    const lanes = [-0.62, 0, 0.62];
    const lane = lanes[Math.floor(Math.random() * lanes.length)];
    const types = [
      { name: 'PETROL_SEDAN', color: '#f87171', speed: 85, w: 42, h: 22 },
      { name: 'DELIVERY_VAN', color: '#fbbf24', speed: 70, w: 46, h: 26 },
      { name: 'OLD_TRUCK', color: '#94a3b8', speed: 60, w: 50, h: 30 }
    ];
    const type = types[Math.floor(Math.random() * types.length)];

    this.traffic.push({
      x: lane,
      z: distZ,
      speed: type.speed,
      color: type.color,
      w: type.w,
      h: type.h,
      type: type.name,
      overtaken: false
    });
  }

  _spawnItem(distZ) {
    const lanes = [-0.62, 0, 0.62];
    const lane = lanes[Math.floor(Math.random() * lanes.length)];
    const isSolar = Math.random() < 0.28;

    this.items.push({
      x: lane,
      z: distZ,
      type: isSolar ? 'SOLAR_ORB' : 'BATTERY_PACK',
      pulse: 0
    });
  }

  // ── MAIN LOOP ──
  _loop() {
    if (!this.isRunning || this.isPaused) return;

    const now = performance.now();
    const dt = Math.min((now - this.lastTimestamp) / 1000, 0.1);
    this.lastTimestamp = now;

    this._update(dt);
    this._render();

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  // ── PHYSICS & LOGIC UPDATE ──
  _update(dt) {
    // 1. Steering Physics
    const steerRate = this.speed > 250 ? 2.8 : 2.3;
    if (this.keys.left) {
      this.targetX = Math.max(-0.85, this.targetX - steerRate * dt);
    }
    if (this.keys.right) {
      this.targetX = Math.min(0.85, this.targetX + steerRate * dt);
    }
    // Smooth damp towards target
    this.playerX += (this.targetX - this.playerX) * Math.min(1.0, 15 * dt);

    // 2. Speed & Acceleration Mechanics
    if (this.keys.up && this.battery > 5) {
      // Turbo Boost
      this.isBoosting = true;
      this.isBraking = false;
      this.speed = Math.min(this.boostSpeed, this.speed + 280 * dt);
      this.battery = Math.max(0, this.battery - 2.0 * dt); // Consumes energy
    } else if (this.keys.down) {
      // Regenerative Braking
      this.isBraking = true;
      this.isBoosting = false;
      this.speed = Math.max(this.brakeSpeed, this.speed - 240 * dt);
      this.battery = Math.min(this.batteryMax, this.battery + 0.65 * dt); // Regenerates power!
    } else {
      this.isBoosting = false;
      this.isBraking = false;
      // Normal cruise deceleration / acceleration towards baseSpeed
      if (this.speed < this.baseSpeed) {
        this.speed = Math.min(this.baseSpeed, this.speed + 140 * dt);
      } else if (this.speed > this.baseSpeed) {
        this.speed = Math.max(this.baseSpeed, this.speed - 90 * dt);
      }
      // Normal cruise drain
      this.battery = Math.max(0, this.battery - 0.5 * dt);
    }

    // Battery Depletion Check
    if (this.battery <= 0.05) {
      this._gameOver('OUT_OF_BATTERY');
      return;
    }

    // 3. Distance & Score Advancement
    const distDelta = (this.speed * 1000 / 3600) * dt; // meters
    this.totalDistance += distDelta;
    this.roadZ += distDelta;

    const scoreGained = Math.round(distDelta * 1.8 * (this.isBoosting ? 1.5 : 1.0));
    if (this.framework && typeof this.framework.addScore === 'function') {
      this.framework.addScore(scoreGained);
    }
    if (this.framework && typeof this.framework.setDistanceTravelled === 'function') {
      this.framework.setDistanceTravelled(Math.round(this.totalDistance));
    }

    // Level Scaling every 350m: dynamically accelerates speed as player advances levels!
    const currentLevel = Math.floor(this.totalDistance / 350) + 1;
    const prevLevel = (this.framework && this.framework.level) ? this.framework.level : 1;
    if (currentLevel !== prevLevel) {
      if (this.framework && typeof this.framework.setLevel === 'function') {
        this.framework.setLevel(currentLevel);
      }
      const levelSpeedBonus = (currentLevel - 1) * 20; // +20 km/h per level!
      this.baseSpeed = (this.modeBaseSpeed || 190) + levelSpeedBonus;
      this.maxSpeed = (this.modeMaxSpeed || 290) + levelSpeedBonus;
      this.boostSpeed = (this.modeBoostSpeed || 380) + levelSpeedBonus;

      // Instantly surge speed into the new level
      this.speed = Math.max(this.speed, this.baseSpeed);

      // Trigger level-up banner, screen surge, and audio chime
      this.levelUpBannerTimer = 2.4;
      this.levelUpText = `⚡ LEVEL ${currentLevel} REACHED! SPEED +${levelSpeedBonus} KM/H`;
      this.shakeDuration = 0.22;
      this.shakeIntensity = 5;

      for (let s = 0; s < 14; s++) {
        this.speedLines.push({
          x: (Math.random() - 0.5) * this.canvas.width * 1.2 + this.canvas.width / 2,
          y: Math.random() * this.canvas.height * 0.7,
          len: 55 + Math.random() * 85,
          speed: 1200 + Math.random() * 800
        });
      }

      if (window.gameAudio && typeof window.gameAudio.playScore === 'function') {
        window.gameAudio.playScore();
      }
    }

    // 4. Dynamic Road Curvature
    this.curveTimer -= dt;
    if (this.curveTimer <= 0) {
      this.targetCurvature = (Math.random() - 0.5) * 1.4;
      this.curveTimer = 3.5 + Math.random() * 3.0;
    }
    this.roadCurvature += (this.targetCurvature - this.roadCurvature) * (1.2 * dt);

    // 5. Traffic Vehicles Update
    for (let i = this.traffic.length - 1; i >= 0; i--) {
      const car = this.traffic[i];
      // Relative motion: player speed vs other car speed
      const relSpeed = (this.speed - car.speed) * (1000 / 3600);
      car.z -= relSpeed * dt;

      // Check Overtake Bonus
      if (!car.overtaken && car.z < 80 && car.z > -40) {
        if (Math.abs(this.playerX - car.x) > 0.35) {
          car.overtaken = true;
          // Near miss overtake reward
          if (this.framework && typeof this.framework.addScore === 'function') {
            this.framework.addScore(250);
          }
          this._spawnSparks(this.playerX, 0, '#38bdf8', 6);
        }
      }

      // Collision Detection with Player (Player is at z=60, x=playerX)
      if (car.z > 30 && car.z < 85) {
        if (Math.abs(this.playerX - car.x) < 0.28) {
          // Collision occurred!
          this._handleCarCollision(car);
        }
      }

      // Recycle vehicle once far behind or far ahead
      if (car.z < -100) {
        this.traffic.splice(i, 1);
        const maxZ = Math.max(...this.traffic.map(t => t.z), 600);
        this._spawnTraffic(maxZ + 350 + Math.random() * 200);
      }
    }

    // 6. Energy Collectibles Update
    for (let i = this.items.length - 1; i >= 0; i--) {
      const item = this.items[i];
      const relSpeed = this.speed * (1000 / 3600);
      item.z -= relSpeed * dt;
      item.pulse += dt * 5;

      // Pickup Check
      if (item.z > 25 && item.z < 85) {
        if (Math.abs(this.playerX - item.x) < 0.32) {
          this._collectItem(item);
          this.items.splice(i, 1);
          continue;
        }
      }

      // Recycle item if passed
      if (item.z < -40) {
        this.items.splice(i, 1);
        const maxZ = Math.max(...this.items.map(it => it.z), 400);
        this._spawnItem(maxZ + 280 + Math.random() * 180);
      }
    }

    // 7. Speed lines & FX
    const showSpeedLines = this.isBoosting || this.speed > 220;
    if (showSpeedLines) {
      const lineChance = this.isBoosting ? 0.8 : Math.min(0.7, (this.speed - 220) / 160);
      if (Math.random() < lineChance) {
        this.speedLines.push({
          x: (Math.random() - 0.5) * this.canvas.width * 1.2 + this.canvas.width / 2,
          y: Math.random() * this.canvas.height * 0.7,
          len: 45 + Math.random() * 85,
          speed: 900 + Math.random() * 800
        });
      }
    }

    for (let i = this.speedLines.length - 1; i >= 0; i--) {
      const sl = this.speedLines[i];
      sl.y += sl.speed * dt;
      if (sl.y > this.canvas.height) this.speedLines.splice(i, 1);
    }

    // Update Particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.life -= dt;
      if (p.life <= 0) this.particles.splice(i, 1);
    }

    // Screen Shake decay & Banner Timer
    if (this.shakeDuration > 0) {
      this.shakeDuration -= dt;
    }
    if (this.levelUpBannerTimer > 0) {
      this.levelUpBannerTimer -= dt;
    }
  }

  _collectItem(item) {
    this.batteryPacksCollected++;
    if (this.framework && typeof this.framework.addItemsCollected === 'function') {
      this.framework.addItemsCollected(1);
    }

    if (item.type === 'SOLAR_ORB') {
      // Golden Solar Orb: +15% battery, +400 points
      this.battery = Math.min(this.batteryMax, this.battery + 15.0);
      if (this.framework && typeof this.framework.addScore === 'function') {
        this.framework.addScore(400);
      }
      this._spawnSparks(this.playerX, 0, '#f59e0b', 14);
    } else {
      // Green Battery Pack: +25% battery, +250 points
      this.battery = Math.min(this.batteryMax, this.battery + 25.0);
      if (this.framework && typeof this.framework.addScore === 'function') {
        this.framework.addScore(250);
      }
      this._spawnSparks(this.playerX, 0, '#10b981', 12);
    }

    // Play chime sound
    if (window.gameAudio && typeof window.gameAudio.playFoodBeep === 'function') {
      window.gameAudio.playFoodBeep();
    }
  }

  _handleCarCollision(car) {
    this.shakeDuration = 0.35;
    this.shakeIntensity = 8;
    this.speed = Math.max(40, this.speed - 70);
    this.battery = Math.max(0, this.battery - 18.0);

    // Push other car away
    car.z += 80;
    this._spawnSparks(this.playerX, 0, '#ef4444', 20);

    // Check if fatal collision / dead battery
    if (this.battery <= 0.05) {
      this._gameOver('CRASH_AND_DRAIN');
    }
  }

  _spawnSparks(px, py, color, count) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const originX = w / 2 + px * (w * 0.38);
    const originY = h - 65;

    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 80 + Math.random() * 160;
      this.particles.push({
        x: originX,
        y: originY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        color: color,
        radius: 2 + Math.random() * 2.5,
        life: 0.35 + Math.random() * 0.3
      });
    }
  }

  _gameOver(reason) {
    this.isRunning = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    if (window.gameAudio && typeof window.gameAudio.playGameOver === 'function') {
      window.gameAudio.playGameOver();
    }

    if (this.framework && typeof this.framework.gameOver === 'function') {
      this.framework.gameOver({
        score: this.framework.score,
        itemsCollected: this.batteryPacksCollected,
        distanceTravelled: Math.round(this.totalDistance),
        level: this.framework.level
      });
    }
  }

  // ── RENDERING ENGINE ──
  _render() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    this.ctx.save();

    // Screen Shake
    if (this.shakeDuration > 0) {
      const sx = (Math.random() - 0.5) * this.shakeIntensity;
      const sy = (Math.random() - 0.5) * this.shakeIntensity;
      this.ctx.translate(sx, sy);
    }

    // 1. Cyber Skyline & Sunset Gradient
    this._drawSkyline(w, h);

    // 2. Horizon & 3D Perspective Road
    this._drawRoad(w, h);

    // 3. Render Collectibles (Sorted by Z depth)
    this._renderItems(w, h);

    // 4. Render Traffic Vehicles (Sorted by Z depth)
    this._renderTraffic(w, h);

    // 5. Render Player's High-Tech EV Car
    this._drawPlayerCar(w, h);

    // 6. Visual Speedlines & Particles
    this._drawSpeedLines();
    this._drawParticles();

    // 7. HUD Overlays (Battery & Speedometer)
    this._drawHUD(w, h);

    this.ctx.restore();
  }

  _drawSkyline(w, h) {
    const horizonY = h * 0.44;

    // Dark cyberpunk sky gradient
    const skyGrad = this.ctx.createLinearGradient(0, 0, 0, horizonY);
    skyGrad.addColorStop(0, '#090d16');
    skyGrad.addColorStop(0.5, '#111827');
    skyGrad.addColorStop(0.85, '#1e1b4b');
    skyGrad.addColorStop(1, '#312e81');
    this.ctx.fillStyle = skyGrad;
    this.ctx.fillRect(0, 0, w, horizonY);

    // Neon Cyber Sun / Moon
    const sunX = w * 0.72 + this.roadCurvature * 40;
    const sunY = horizonY * 0.65;
    const sunGrad = this.ctx.createRadialGradient(sunX, sunY, 6, sunX, sunY, 38);
    sunGrad.addColorStop(0, '#38bdf8');
    sunGrad.addColorStop(0.4, 'rgba(56, 189, 248, 0.4)');
    sunGrad.addColorStop(1, 'rgba(56, 189, 248, 0)');
    this.ctx.fillStyle = sunGrad;
    this.ctx.beginPath();
    this.ctx.arc(sunX, sunY, 38, 0, Math.PI * 2);
    this.ctx.fill();

    // Futuristic Neon Skyline Silhouettes
    this.ctx.fillStyle = '#0a0f1d';
    const buildingWidths = [36, 48, 28, 54, 40, 32, 60, 44, 38, 50, 30, 46];
    let curX = -20 - (this.roadCurvature * 30);
    for (let i = 0; curX < w + 40; i++) {
      const bw = buildingWidths[i % buildingWidths.length];
      const bh = 45 + ((i * 19) % 55);
      this.ctx.fillRect(curX, horizonY - bh, bw, bh);

      // Glowing Neon Windows
      if (i % 2 === 0) {
        this.ctx.fillStyle = i % 4 === 0 ? 'rgba(56, 189, 248, 0.6)' : 'rgba(245, 158, 11, 0.6)';
        this.ctx.fillRect(curX + 6, horizonY - bh + 8, bw - 12, 3);
        this.ctx.fillStyle = '#0a0f1d';
      }
      curX += bw + 4;
    }
  }

  _drawRoad(w, h) {
    const horizonY = h * 0.44;
    const roadBottomW = w * 0.94;
    const roadTopW = w * 0.16;

    const curveOffset = this.roadCurvature * (w * 0.18);
    const horizonX = w / 2 + curveOffset;

    // Landscape Grass / Cyber Grid below horizon
    this.ctx.fillStyle = '#090d16';
    this.ctx.fillRect(0, horizonY, w, h - horizonY);

    // Road Polygon
    this.ctx.fillStyle = '#141824';
    this.ctx.beginPath();
    this.ctx.moveTo(w / 2 - roadBottomW / 2, h);
    this.ctx.lineTo(horizonX - roadTopW / 2, horizonY);
    this.ctx.lineTo(horizonX + roadTopW / 2, horizonY);
    this.ctx.lineTo(w / 2 + roadBottomW / 2, h);
    this.ctx.closePath();
    this.ctx.fill();

    // Road Edge Curbs (Neon Cyan Glowing Strips)
    this.ctx.lineWidth = 3.5;
    this.ctx.strokeStyle = '#38bdf8';
    this.ctx.shadowColor = '#38bdf8';
    this.ctx.shadowBlur = 8;
    this.ctx.beginPath();
    this.ctx.moveTo(w / 2 - roadBottomW / 2, h);
    this.ctx.lineTo(horizonX - roadTopW / 2, horizonY);
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.moveTo(w / 2 + roadBottomW / 2, h);
    this.ctx.lineTo(horizonX + roadTopW / 2, horizonY);
    this.ctx.stroke();
    this.ctx.shadowBlur = 0;

    // Moving Dashed Lane Dividers (3-Lane Road)
    const numDashes = 14;
    const dashOffset = (this.roadZ % 45) / 45; // 0 to 1

    for (let i = 0; i < numDashes; i++) {
      const p1 = (i + dashOffset) / numDashes;
      const p2 = (i + dashOffset + 0.5) / numDashes;

      if (p1 > 1.0) continue;

      const y1 = horizonY + (h - horizonY) * Math.pow(p1, 2);
      const y2 = horizonY + (h - horizonY) * Math.pow(Math.min(1.0, p2), 2);

      const rWidth1 = roadTopW + (roadBottomW - roadTopW) * Math.pow(p1, 2);
      const rWidth2 = roadTopW + (roadBottomW - roadTopW) * Math.pow(Math.min(1.0, p2), 2);

      const hX1 = horizonX + (w / 2 - horizonX) * p1;
      const hX2 = horizonX + (w / 2 - horizonX) * p2;

      // Lane 1 divider (-0.33)
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.45)';
      this.ctx.lineWidth = Math.max(1.2, 4 * p1);
      this.ctx.beginPath();
      this.ctx.moveTo(hX1 - rWidth1 * 0.17, y1);
      this.ctx.lineTo(hX2 - rWidth2 * 0.17, y2);
      this.ctx.stroke();

      // Lane 2 divider (+0.33)
      this.ctx.beginPath();
      this.ctx.moveTo(hX1 + rWidth1 * 0.17, y1);
      this.ctx.lineTo(hX2 + rWidth2 * 0.17, y2);
      this.ctx.stroke();
    }
  }

  _renderItems(w, h) {
    const horizonY = h * 0.44;
    const roadBottomW = w * 0.94;
    const roadTopW = w * 0.16;
    const curveOffset = this.roadCurvature * (w * 0.18);
    const horizonX = w / 2 + curveOffset;

    this.items.forEach(item => {
      if (item.z <= 0 || item.z > 900) return;
      const progress = Math.max(0.01, Math.min(1.0, 1.0 - item.z / 900));
      const perspectiveScale = Math.pow(progress, 2.2);

      const y = horizonY + (h - horizonY) * perspectiveScale;
      const rWidth = roadTopW + (roadBottomW - roadTopW) * perspectiveScale;
      const hX = horizonX + (w / 2 - horizonX) * progress;
      const x = hX + item.x * (rWidth * 0.42);

      const size = Math.max(6, 32 * perspectiveScale);

      // Draw Glowing Energy Item
      if (item.type === 'SOLAR_ORB') {
        // Glowing Gold Solar Orb
        this.ctx.fillStyle = '#f59e0b';
        this.ctx.shadowColor = '#f59e0b';
        this.ctx.shadowBlur = 10 * perspectiveScale;
        this.ctx.beginPath();
        this.ctx.arc(x, y - size, size * 0.85, 0, Math.PI * 2);
        this.ctx.fill();

        // Inner highlight
        this.ctx.fillStyle = '#fffbeb';
        this.ctx.beginPath();
        this.ctx.arc(x - size * 0.25, y - size - size * 0.25, size * 0.35, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;
      } else {
        // Neon Emerald Battery Cell
        this.ctx.fillStyle = '#10b981';
        this.ctx.shadowColor = '#10b981';
        this.ctx.shadowBlur = 10 * perspectiveScale;
        this.ctx.beginPath();
        this.ctx.roundRect(x - size * 0.7, y - size * 1.5, size * 1.4, size * 1.5, 4 * perspectiveScale);
        this.ctx.fill();

        // Bolt Icon
        this.ctx.fillStyle = '#ffffff';
        this.ctx.font = `bold ${Math.round(size * 0.85)}px sans-serif`;
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText('⚡', x, y - size * 0.75);
        this.ctx.shadowBlur = 0;
      }
    });
  }

  _renderTraffic(w, h) {
    const horizonY = h * 0.44;
    const roadBottomW = w * 0.94;
    const roadTopW = w * 0.16;
    const curveOffset = this.roadCurvature * (w * 0.18);
    const horizonX = w / 2 + curveOffset;

    // Sort by Z descending so furthest drawn first
    const sorted = [...this.traffic].sort((a, b) => b.z - a.z);

    sorted.forEach(car => {
      if (car.z <= 0 || car.z > 900) return;
      const progress = Math.max(0.01, Math.min(1.0, 1.0 - car.z / 900));
      const perspectiveScale = Math.pow(progress, 2.2);

      const y = horizonY + (h - horizonY) * perspectiveScale;
      const rWidth = roadTopW + (roadBottomW - roadTopW) * perspectiveScale;
      const hX = horizonX + (w / 2 - horizonX) * progress;
      const x = hX + car.x * (rWidth * 0.42);

      const carW = Math.max(10, car.w * 1.6 * perspectiveScale);
      const carH = Math.max(6, car.h * 1.6 * perspectiveScale);

      // Car Drop Shadow
      this.ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
      this.ctx.fillRect(x - carW / 2, y - 2, carW, 4 * perspectiveScale);

      // Chassis Body
      this.ctx.fillStyle = car.color;
      this.ctx.beginPath();
      this.ctx.roundRect(x - carW / 2, y - carH, carW, carH, 4 * perspectiveScale);
      this.ctx.fill();

      // Rear Windshield
      this.ctx.fillStyle = '#0f172a';
      this.ctx.fillRect(x - carW * 0.35, y - carH * 0.85, carW * 0.7, carH * 0.35);

      // Tail Lights (Red Glow)
      this.ctx.fillStyle = '#ef4444';
      this.ctx.shadowColor = '#ef4444';
      this.ctx.shadowBlur = 6 * perspectiveScale;
      this.ctx.fillRect(x - carW * 0.45, y - carH * 0.3, carW * 0.25, carH * 0.2);
      this.ctx.fillRect(x + carW * 0.2, y - carH * 0.3, carW * 0.25, carH * 0.2);
      this.ctx.shadowBlur = 0;
    });
  }

  _drawPlayerCar(w, h) {
    const carY = h - 34;
    const carX = w / 2 + this.playerX * (w * 0.38);
    const carW = Math.min(84, w * 0.22);
    const carH = carW * 0.52;

    // Floor Shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    this.ctx.beginPath();
    this.ctx.ellipse(carX, carY + 8, carW * 0.55, 6, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // 1. Neon Underglow (Emerald Green / Cyan for EV identity)
    const underglowColor = this.isBoosting ? '#38bdf8' : (this.isBraking ? '#ef4444' : '#10b981');
    this.ctx.shadowColor = underglowColor;
    this.ctx.shadowBlur = 18;
    this.ctx.fillStyle = underglowColor;
    this.ctx.fillRect(carX - carW * 0.4, carY + 2, carW * 0.8, 3);
    this.ctx.shadowBlur = 0;

    // 2. Wide Racing Tires
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(carX - carW * 0.52, carY - carH * 0.5, carW * 0.16, carH * 0.65);
    this.ctx.fillRect(carX + carW * 0.36, carY - carH * 0.5, carW * 0.16, carH * 0.65);

    // 3. Aerodynamic Metallic Supercar Body
    const bodyGrad = this.ctx.createLinearGradient(carX, carY - carH, carX, carY);
    bodyGrad.addColorStop(0, '#1e293b');
    bodyGrad.addColorStop(0.3, '#334155');
    bodyGrad.addColorStop(0.7, '#0f172a');
    bodyGrad.addColorStop(1, '#020617');
    this.ctx.fillStyle = bodyGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(carX - carW * 0.45, carY - carH, carW * 0.9, carH, 8);
    this.ctx.fill();

    // 4. Tinted Aero Cockpit Dome
    const glassGrad = this.ctx.createLinearGradient(carX, carY - carH, carX, carY - carH * 0.4);
    glassGrad.addColorStop(0, '#38bdf8');
    glassGrad.addColorStop(0.5, '#0284c7');
    glassGrad.addColorStop(1, '#0f172a');
    this.ctx.fillStyle = glassGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(carX - carW * 0.3, carY - carH * 0.9, carW * 0.6, carH * 0.45, 5);
    this.ctx.fill();

    // 5. Specular Cockpit Catchlight
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    this.ctx.fillRect(carX - carW * 0.22, carY - carH * 0.85, carW * 0.12, carH * 0.12);

    // 6. Rear LED Ribbon Tail Lights
    const tailColor = this.isBraking ? '#ef4444' : '#f43f5e';
    this.ctx.shadowColor = tailColor;
    this.ctx.shadowBlur = this.isBraking ? 16 : 8;
    this.ctx.fillStyle = tailColor;
    this.ctx.fillRect(carX - carW * 0.42, carY - carH * 0.22, carW * 0.84, carH * 0.14);
    this.ctx.shadowBlur = 0;

    // 7. MyntReal / Zynova Brand Accent Emblem
    this.ctx.fillStyle = '#10b981';
    this.ctx.beginPath();
    this.ctx.arc(carX, carY - carH * 0.35, 3.5, 0, Math.PI * 2);
    this.ctx.fill();

    // 8. Turbo Boost Exhaust Plasma Jets
    if (this.isBoosting) {
      this.ctx.fillStyle = '#38bdf8';
      this.ctx.shadowColor = '#38bdf8';
      this.ctx.shadowBlur = 14;
      this.ctx.beginPath();
      this.ctx.moveTo(carX - carW * 0.25, carY);
      this.ctx.lineTo(carX - carW * 0.20, carY + 16 + Math.random() * 8);
      this.ctx.lineTo(carX - carW * 0.15, carY);
      this.ctx.fill();

      this.ctx.beginPath();
      this.ctx.moveTo(carX + carW * 0.15, carY);
      this.ctx.lineTo(carX + carW * 0.20, carY + 16 + Math.random() * 8);
      this.ctx.lineTo(carX + carW * 0.25, carY);
      this.ctx.fill();
      this.ctx.shadowBlur = 0;
    }
  }

  _drawSpeedLines() {
    this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.45)';
    this.ctx.lineWidth = 1.8;
    this.speedLines.forEach(sl => {
      this.ctx.beginPath();
      this.ctx.moveTo(sl.x, sl.y);
      this.ctx.lineTo(sl.x, sl.y + sl.len);
      this.ctx.stroke();
    });
  }

  _drawParticles() {
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fill();
    });
  }

  _drawHUD(w, h) {
    // ── TOP LEFT: BATTERY HUD BAR ──
    const batW = Math.min(130, w * 0.32);
    const batH = 12;
    const batX = 14;
    const batY = 14;

    this.ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.18)';
    this.ctx.lineWidth = 1.2;
    this.ctx.beginPath();
    this.ctx.roundRect(batX, batY, batW, batH, 4);
    this.ctx.fill();
    this.ctx.stroke();

    // Fill level
    const batPct = Math.max(0, Math.min(100, this.battery));
    const fillW = (batPct / 100) * (batW - 4);
    let fillCol = '#10b981';
    if (batPct < 25) fillCol = '#ef4444';
    else if (batPct < 50) fillCol = '#f59e0b';

    this.ctx.fillStyle = fillCol;
    this.ctx.beginPath();
    this.ctx.roundRect(batX + 2, batY + 2, fillW, batH - 4, 2);
    this.ctx.fill();

    // Battery Text
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '800 10px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'left';
    this.ctx.fillText(`⚡ BATTERY ${Math.round(batPct)}%`, batX, batY + batH + 13);

    // ── TOP RIGHT: SPEEDOMETER & REGEN HUD ──
    const spdText = `${Math.round(this.speed)} KM/H`;
    this.ctx.fillStyle = this.isBoosting ? '#38bdf8' : (this.isBraking ? '#ef4444' : '#f8fafc');
    this.ctx.font = '900 16px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'right';
    this.ctx.fillText(spdText, w - 14, 26);

    let modeText = 'ECO CRUISE';
    let modeCol = '#94a3b8';
    if (this.isBoosting) {
      modeText = '⚡ TURBO BOOST';
      modeCol = '#38bdf8';
    } else if (this.isBraking) {
      modeText = '🛡️ REGEN BRAKE (+CHARGE)';
      modeCol = '#10b981';
    }
    this.ctx.fillStyle = modeCol;
    this.ctx.font = '700 9.5px "Plus Jakarta Sans", sans-serif';
    this.ctx.fillText(modeText, w - 14, 40);

    // Distance Tracker
    this.ctx.fillStyle = '#cbd5e1';
    this.ctx.font = '600 10px "Plus Jakarta Sans", sans-serif';
    this.ctx.fillText(`📍 ${Math.round(this.totalDistance)}m | 🔋 ${this.batteryPacksCollected}`, w - 14, 54);

    // ── LEVEL UP NOTIFICATION BANNER ──
    if (this.levelUpBannerTimer > 0) {
      this.ctx.save();
      const alpha = Math.min(1.0, this.levelUpBannerTimer * 1.5);
      this.ctx.globalAlpha = alpha;
      this.ctx.fillStyle = 'rgba(16, 185, 129, 0.92)';
      this.ctx.strokeStyle = '#34d399';
      this.ctx.lineWidth = 1.5;
      const bW = Math.min(320, w * 0.90);
      const bH = 34;
      const bX = (w - bW) / 2;
      const bY = h * 0.40;
      this.ctx.beginPath();
      this.ctx.roundRect(bX, bY, bW, bH, 8);
      this.ctx.fill();
      this.ctx.stroke();

      this.ctx.fillStyle = '#ffffff';
      this.ctx.font = '900 12px "Plus Jakarta Sans", sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(this.levelUpText || 'LEVEL UP! SPEED BOOSTED!', w / 2, bY + 21);
      this.ctx.restore();
    }
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#38bdf8';
    this.ctx.font = '800 18px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('⚡ EV RACER 3D', w / 2, h / 2 - 14);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 12px "Plus Jakarta Sans", sans-serif';
    this.ctx.fillText('Tap "Start Game" to race & collect energy cells', w / 2, h / 2 + 14);
  }
}
