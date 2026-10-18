/**
 * Game F: Bounce Classic 3D (Inspired by the legendary Nokia mobile classic)
 * DC Protocol Oct 2026.
 * Red rubber bouncy ball platformer with continuous bounce & squish physics,
 * floating golden hoops, collectible stars, navigating spike hazards,
 * trampolines/jump pads, solid world boundaries, unlockable exit portals,
 * adjustable speed modes, and anti-cheat validation.
 */

class BounceClassicGame {
  constructor(canvas, framework) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.framework = framework;

    this.radius = 16;
    this.x = 60;
    this.y = 100;
    this.vx = 0;
    this.vy = 0;
    this.rotation = 0;

    // Squish & stretch deformation factors
    this.squishX = 1.0;
    this.squishY = 1.0;

    // Speed mode settings
    this.speedMode = 'NORMAL';
    this.moveSpeed = 3.8;
    this.superBounceVy = -11.0;
    this.gravity = 0.44;
    this.bounceCoeff = -0.74; // Natural rubber rebound
    this.friction = 0.92;
    this.isGrounded = false;

    // Camera viewport offset & World boundaries
    this.cameraX = 0;
    this.worldWidth = 1620;
    this.lastSafeX = 60;

    // Game stats
    this.lives = 3;
    this.level = 1;
    this.totalHoops = 0;
    this.collectedHoops = 0;
    this.nearLockedPortal = false;

    // World elements
    this.platforms = [];
    this.jumpPads = [];
    this.hoops = [];
    this.spikes = [];
    this.gems = [];
    this.portal = null;
    this.particles = [];

    this.keys = { left: false, right: false, up: false };

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  setSpeedMode(mode) {
    this.speedMode = mode;
    if (mode === 'SLOW') {
      this.moveSpeed = 2.6;
      this.superBounceVy = -9.6;
    } else if (mode === 'FAST') {
      this.moveSpeed = 5.0;
      this.superBounceVy = -12.4;
    } else if (mode === 'TURBO') {
      this.moveSpeed = 6.4;
      this.superBounceVy = -13.8;
    } else { // NORMAL
      this.moveSpeed = 3.8;
      this.superBounceVy = -11.0;
    }
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentWidth = this.canvas.parentElement.clientWidth;
    const w = Math.min(parentWidth - 16, 540);
    const h = Math.min(window.innerHeight * 0.44, 460);

    this.canvas.width = w;
    this.canvas.height = h;

    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused) return;

      if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
        this.keys.left = true;
      } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
        this.keys.right = true;
      } else if (e.code === 'ArrowUp' || e.code === 'KeyW' || e.code === 'Space') {
        e.preventDefault();
        this.superBounce();
      }
    });

    window.addEventListener('keyup', (e) => {
      if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
        this.keys.left = false;
      } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
        this.keys.right = false;
      }
    });

    // Touch & pointer controls on canvas
    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.isRunning || this.isPaused) return;
      const rect = this.canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;

      if (clickX < rect.width * 0.35) {
        this.keys.left = true;
      } else if (clickX > rect.width * 0.65) {
        this.keys.right = true;
      } else {
        this.superBounce();
      }
    });

    this.canvas.addEventListener('pointerup', () => {
      this.keys.left = false;
      this.keys.right = false;
    });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  moveLeft(active = true) {
    this.keys.left = active;
  }

  moveRight(active = true) {
    this.keys.right = active;
  }

  superBounce() {
    // Jump higher if grounded or near a bounce peak
    if (this.isGrounded || Math.abs(this.vy) < 3.5) {
      this.vy = this.superBounceVy;
      this.isGrounded = false;
      this.squishX = 0.75;
      this.squishY = 1.35;
      if (window.gameAudio && typeof window.gameAudio.playBallBounce === 'function') {
        window.gameAudio.playBallBounce(true);
      }
    }
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this._buildLevel(this.level);
    this._loop();
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this._loop();
  }

  reset() {
    this.isRunning = false;
    this.isPaused = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    this.x = 60;
    this.y = 100;
    this.vx = 0;
    this.vy = 0;
    this.lives = 3;
    this.level = 1;
    this.cameraX = 0;
    this.lastSafeX = 60;
    this.nearLockedPortal = false;
    this.collectedHoops = 0;
    this.totalHoops = 0;
    this.particles = [];
    this.keys = { left: false, right: false, up: false };
  }

  _buildLevel(lvl) {
    const floorY = this.canvas.height - 35;
    this.worldWidth = 1580;
    this.x = 60;
    this.y = floorY - 50;
    this.vx = 0;
    this.vy = 0;
    this.cameraX = 0;
    this.lastSafeX = 60;
    this.collectedHoops = 0;
    this.nearLockedPortal = false;
    this.particles = [];

    // Continuous floor + solid Left and Right end boundary walls
    this.platforms = [
      // Floor
      { x: -30, y: floorY, w: this.worldWidth + 60, h: 60, type: 'FLOOR' },
      // Left boundary wall (cannot go off left)
      { x: -20, y: 0, w: 28, h: floorY + 60, type: 'WALL' },
      // Right boundary wall (cannot roll off into abyss past portal)
      { x: this.worldWidth - 10, y: 0, w: 30, h: floorY + 60, type: 'WALL' }
    ];

    // Stepped elevated platforms
    this.platforms.push(
      { x: 170, y: floorY - 55, w: 130, h: 18, type: 'BRICK' },
      { x: 370, y: floorY - 105, w: 140, h: 18, type: 'BRICK' },
      { x: 580, y: floorY - 60, w: 130, h: 18, type: 'BRICK' },
      { x: 770, y: floorY - 115, w: 150, h: 18, type: 'BRICK' },
      { x: 1000, y: floorY - 75, w: 140, h: 18, type: 'BRICK' },
      { x: 1200, y: floorY - 120, w: 140, h: 18, type: 'BRICK' }
    );

    // Trampolines / Super Bounce Pads (classic Nokia springboards)
    this.jumpPads = [
      { x: 330, y: floorY - 8, w: 46, h: 8 },
      { x: 940, y: floorY - 8, w: 46, h: 8 }
    ];

    // Spike Hazards (pop the ball!)
    this.spikes = [
      { x: 530, y: floorY - 16, w: 36, h: 16 },
      { x: 720, y: floorY - 16, w: 36, h: 16 },
      { x: 1150, y: floorY - 16, w: 36, h: 16 }
    ];

    // Floating Golden Hoops (Nokia Bounce Signature!)
    this.hoops = [
      { x: 235, y: floorY - 105, radius: 24, collected: false },
      { x: 440, y: floorY - 160, radius: 24, collected: false }, // Reachable via Trampoline 1!
      { x: 645, y: floorY - 110, radius: 24, collected: false },
      { x: 845, y: floorY - 165, radius: 24, collected: false },
      { x: 1070, y: floorY - 125, radius: 24, collected: false }, // Reachable via Trampoline 2!
      { x: 1270, y: floorY - 170, radius: 24, collected: false }
    ];
    this.totalHoops = this.hoops.length;

    // Collectible Gems
    this.gems = [
      { x: 195, y: floorY - 82, collected: false },
      { x: 400, y: floorY - 132, collected: false },
      { x: 605, y: floorY - 88, collected: false },
      { x: 805, y: floorY - 145, collected: false },
      { x: 1030, y: floorY - 102, collected: false }
    ];

    // Goal Portal at the end of the course
    this.portal = {
      x: 1420,
      y: floorY - 76,
      w: 44,
      h: 76,
      unlocked: false
    };
  }

  _loop() {
    if (!this.isRunning || this.isPaused) return;

    try {
      this._update();
      this._draw();
    } catch (err) {
      console.error('[BounceClassic] Loop error:', err);
    }

    this.animFrameId = requestAnimationFrame(() => this._loop());
  }

  _update() {
    // 1. Horizontal acceleration
    if (this.keys.left) {
      this.vx = Math.max(-this.moveSpeed, this.vx - 0.45);
    } else if (this.keys.right) {
      this.vx = Math.min(this.moveSpeed, this.vx + 0.45);
    } else {
      this.vx *= this.friction;
    }

    // Rolling rotation proportional to horizontal speed
    this.rotation += this.vx * 0.08;

    // Apply gravity
    this.vy += this.gravity;

    // Tentative next position
    this.x += this.vx;
    this.y += this.vy;

    // Hard screen / world horizontal clamp
    if (this.x - this.radius < 10) {
      this.x = 10 + this.radius;
      this.vx = Math.abs(this.vx) * 0.5;
    } else if (this.x + this.radius > this.worldWidth - 14) {
      this.x = this.worldWidth - 14 - this.radius;
      this.vx = -Math.abs(this.vx) * 0.5;
    }

    // Recover squish deformation back towards 1.0
    this.squishX += (1.0 - this.squishX) * 0.18;
    this.squishY += (1.0 - this.squishY) * 0.18;

    this.isGrounded = false;

    // 2. Trampoline / Jump Pad Collisions
    for (const jp of this.jumpPads) {
      if (
        this.x + this.radius * 0.7 > jp.x &&
        this.x - this.radius * 0.7 < jp.x + jp.w &&
        this.y + this.radius >= jp.y &&
        this.y - this.radius <= jp.y + jp.h + 8 &&
        this.vy > 0
      ) {
        this.y = jp.y - this.radius;
        this.vy = -13.5; // High launch!
        this.squishX = 0.65;
        this.squishY = 1.45;
        this._spawnSparkles(jp.x + jp.w / 2, jp.y, '#f43f5e');
        if (window.gameAudio && typeof window.gameAudio.playBallBounce === 'function') {
          window.gameAudio.playBallBounce(true);
        }
      }
    }

    // 3. Platform Collisions (AABB test)
    for (const p of this.platforms) {
      if (p.type === 'WALL') {
        // Horizontal wall collision
        if (
          this.x + this.radius > p.x &&
          this.x - this.radius < p.x + p.w &&
          this.y + this.radius > p.y &&
          this.y - this.radius < p.y + p.h
        ) {
          if (this.vx > 0) {
            this.x = p.x - this.radius;
            this.vx = -Math.abs(this.vx) * 0.6;
          } else if (this.vx < 0) {
            this.x = p.x + p.w + this.radius;
            this.vx = Math.abs(this.vx) * 0.6;
          }
        }
      } else {
        // Floor & Brick platform collisions
        if (
          this.x + this.radius > p.x &&
          this.x - this.radius < p.x + p.w &&
          this.y + this.radius >= p.y &&
          this.y - this.radius <= p.y + p.h
        ) {
          // Landing from top
          if (this.vy > 0 && this.y - this.vy + this.radius <= p.y + 12) {
            this.y = p.y - this.radius;
            this.isGrounded = true;
            this.lastSafeX = this.x; // Record safe platform checkpoint

            // Natural bounce if landing with enough speed
            if (Math.abs(this.vy) > 1.8) {
              this.vy = this.vy * this.bounceCoeff;
              this.squishX = 1.25;
              this.squishY = 0.72;
              if (window.gameAudio && typeof window.gameAudio.playBallBounce === 'function') {
                window.gameAudio.playBallBounce(false);
              }
            } else {
              this.vy = 0;
            }
          }
        }
      }
    }

    // 4. Spike Hazards Collision (Popping the ball)
    for (const s of this.spikes) {
      if (
        this.x + this.radius * 0.65 > s.x &&
        this.x - this.radius * 0.65 < s.x + s.w &&
        this.y + this.radius * 0.65 > s.y &&
        this.y - this.radius * 0.65 < s.y + s.h
      ) {
        this._handlePop();
        return;
      }
    }

    // 5. Golden Hoops (Passing through rings)
    for (const hoop of this.hoops) {
      if (!hoop.collected) {
        const dx = this.x - hoop.x;
        const dy = this.y - hoop.y;
        const dist = Math.hypot(dx, dy);

        if (dist < hoop.radius + this.radius * 0.5) {
          hoop.collected = true;
          this.collectedHoops++;
          if (this.framework && typeof this.framework.addScore === 'function') {
            this.framework.addScore(200);
          }
          if (this.framework && typeof this.framework.addItemsCollected === 'function') {
            this.framework.addItemsCollected(1);
          }
          this._spawnSparkles(hoop.x, hoop.y, '#f59e0b');
          if (window.gameAudio && typeof window.gameAudio.playHoopPass === 'function') {
            window.gameAudio.playHoopPass();
          }

          // If all hoops collected, unlock the Exit Goal Portal!
          if (this.collectedHoops >= this.totalHoops && this.portal) {
            this.portal.unlocked = true;
            this._spawnSparkles(this.portal.x + this.portal.w / 2, this.portal.y + this.portal.h / 2, '#38bdf8');
            if (window.gameAudio && typeof window.gameAudio.playPowerup === 'function') {
              window.gameAudio.playPowerup();
            }
          }
        }
      }
    }

    // 6. Collectible Gems
    for (const gem of this.gems) {
      if (!gem.collected) {
        const dx = this.x - gem.x;
        const dy = this.y - gem.y;
        if (Math.hypot(dx, dy) < this.radius + 10) {
          gem.collected = true;
          if (this.framework && typeof this.framework.addScore === 'function') {
            this.framework.addScore(100);
          }
          this._spawnSparkles(gem.x, gem.y, '#10b981');
          if (window.gameAudio && typeof window.gameAudio.playCollect === 'function') {
            window.gameAudio.playCollect();
          }
        }
      }
    }

    // 7. Exit Goal Portal (Solid when Locked, Enters when Unlocked)
    if (this.portal) {
      const portalCenterX = this.portal.x + this.portal.w / 2;
      const portalCenterY = this.portal.y + this.portal.h / 2;
      const distToPortal = Math.hypot(this.x - portalCenterX, this.y - portalCenterY);

      this.nearLockedPortal = (!this.portal.unlocked && distToPortal < 190);

      // Check collision with portal archway
      if (
        this.x + this.radius > this.portal.x &&
        this.x - this.radius < this.portal.x + this.portal.w &&
        this.y + this.radius > this.portal.y &&
        this.y - this.radius < this.portal.y + this.portal.h
      ) {
        if (this.portal.unlocked) {
          this._handleLevelComplete();
          return;
        } else {
          // Locked portal is a solid barrier! Gently bounce the ball back
          if (this.x < portalCenterX) {
            this.x = this.portal.x - this.radius;
            this.vx = -Math.abs(this.vx || 3);
          } else {
            this.x = this.portal.x + this.portal.w + this.radius;
            this.vx = Math.abs(this.vx || 3);
          }
          if (window.gameAudio && typeof window.gameAudio.playPaddleHit === 'function') {
            window.gameAudio.playPaddleHit(0);
          }
        }
      }
    }

    // 8. Abyss / Void Fall Safety Check (Ball fell off floor or into depth)
    if (this.y > this.canvas.height + 30) {
      this._handleVoidFall();
      return;
    }

    // 9. Update Particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.alpha -= 0.03;
      if (p.alpha <= 0) {
        this.particles.splice(i, 1);
      }
    }

    // 10. Smooth Camera Tracking
    const targetCamX = this.x - this.canvas.width * 0.35;
    this.cameraX += (targetCamX - this.cameraX) * 0.12;
    this.cameraX = Math.max(0, Math.min(this.worldWidth - this.canvas.width, this.cameraX));
  }

  _handlePop() {
    this._spawnSparkles(this.x, this.y, '#ef4444');
    if (window.gameAudio && typeof window.gameAudio.playCollision === 'function') {
      window.gameAudio.playCollision();
    }

    this.lives--;
    if (this.lives <= 0) {
      this._handleGameOver();
    } else {
      // Respawn at safe start
      this.x = Math.max(60, this.lastSafeX - 60);
      this.y = this.canvas.height - 100;
      this.vx = 0;
      this.vy = -4.0;
    }
  }

  _handleVoidFall() {
    this._spawnSparkles(this.x, this.canvas.height - 10, '#ef4444');
    if (window.gameAudio && typeof window.gameAudio.playCollision === 'function') {
      window.gameAudio.playCollision();
    }

    this.lives--;
    if (this.lives <= 0) {
      this._handleGameOver();
    } else {
      // Respawn safely on the floor
      this.x = Math.max(60, this.lastSafeX);
      this.y = this.canvas.height - 100;
      this.vx = 0;
      this.vy = -4.0;
    }
  }

  _handleLevelComplete() {
    this.level++;
    if (this.framework && typeof this.framework.setLevel === 'function') {
      this.framework.setLevel(this.level);
    }
    if (this.framework && typeof this.framework.addScore === 'function') {
      this.framework.addScore(1000);
    }
    if (window.gameAudio && typeof window.gameAudio.playPowerup === 'function') {
      window.gameAudio.playPowerup();
    }
    this._buildLevel(this.level);
  }

  _handleGameOver() {
    this.isRunning = false;
    if (window.gameAudio && typeof window.gameAudio.playGameOver === 'function') {
      window.gameAudio.playGameOver();
      window.gameAudio.stopMusic();
    }
    if (this.framework && typeof this.framework.gameOver === 'function') {
      this.framework.gameOver({
        score: this.framework.score,
        itemsCollected: this.collectedHoops,
        level: this.level
      });
    }
  }

  _spawnSparkles(x, y, color) {
    for (let i = 0; i < 14; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 3.5 + 1.2;
      this.particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: Math.random() * 2.8 + 1.2,
        color,
        alpha: 1.0
      });
    }
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;

    this.ctx.save();

    // 1. Sky & Horizon Gradient
    const skyGrad = this.ctx.createLinearGradient(0, 0, 0, h);
    skyGrad.addColorStop(0, '#0c1626');
    skyGrad.addColorStop(0.65, '#1e293b');
    skyGrad.addColorStop(1, '#090e17');
    this.ctx.fillStyle = skyGrad;
    this.ctx.fillRect(0, 0, w, h);

    // Apply Camera translation for side-scrolling platformer world
    this.ctx.translate(-this.cameraX, 0);

    // 2. Draw Platforms (Floor, Walls & Bricks)
    this.platforms.forEach(p => {
      this._draw3DPlatform(p);
    });

    // 3. Draw Trampolines / Super Bounce Pads
    this.jumpPads.forEach(jp => {
      this._draw3DJumpPad(jp);
    });

    // 4. Draw Hazard Spikes
    this.spikes.forEach(s => {
      this._draw3DSpike(s);
    });

    // 5. Draw Floating Golden Hoops (Nokia Bounce Signature)
    this.hoops.forEach(hoop => {
      this._draw3DHoop(hoop);
    });

    // 6. Draw Collectible Gems
    this.gems.forEach(gem => {
      if (!gem.collected) {
        this._draw3DGem(gem);
      }
    });

    // 7. Draw Exit Goal Portal with Prominent Status Badge
    if (this.portal) {
      this._draw3DPortal(this.portal);
    }

    // 8. Draw Ball Drop Shadow
    const shadowY = this.canvas.height - 35;
    const shadowDist = Math.max(0, shadowY - this.y);
    const shadowScale = Math.max(0.4, 1.0 - shadowDist / 120);
    this.ctx.fillStyle = `rgba(0, 0, 0, ${0.45 * shadowScale})`;
    this.ctx.beginPath();
    this.ctx.ellipse(this.x, shadowY + 2, this.radius * shadowScale, 5 * shadowScale, 0, 0, Math.PI * 2);
    this.ctx.fill();

    // 9. Draw 3D Red Rubber Ball with Squish & Rolling Rotation
    this._draw3DBall();

    // 10. Draw Sparkle Particles
    this.particles.forEach(p => {
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = p.alpha;
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1.0;

    this.ctx.restore();

    // 11. Fixed HUD Overlay (Hearts, Hoops Counter & Guidance Banner)
    this._drawHUD(w, h);
  }

  _draw3DBall() {
    this.ctx.save();
    this.ctx.translate(this.x, this.y);
    this.ctx.rotate(this.rotation);
    this.ctx.scale(this.squishX, this.squishY);

    const r = this.radius;

    // 3D Red Spherical Gradient
    const ballGrad = this.ctx.createRadialGradient(
      -r * 0.35,
      -r * 0.35,
      r * 0.08,
      0,
      0,
      r
    );
    ballGrad.addColorStop(0, '#ffffff');
    ballGrad.addColorStop(0.25, '#fca5a5');
    ballGrad.addColorStop(0.70, '#ef4444');
    ballGrad.addColorStop(1, '#991b1b');

    this.ctx.fillStyle = ballGrad;
    this.ctx.beginPath();
    this.ctx.arc(0, 0, r, 0, Math.PI * 2);
    this.ctx.fill();

    // Subtle 3D rubber seam line (shows rolling rotation)
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    this.ctx.lineWidth = 1.5;
    this.ctx.beginPath();
    this.ctx.ellipse(0, 0, r * 0.9, r * 0.35, 0, 0, Math.PI * 2);
    this.ctx.stroke();

    // Specular Catchlight Gleam
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    this.ctx.beginPath();
    this.ctx.ellipse(-r * 0.35, -r * 0.35, r * 0.28, r * 0.16, -Math.PI / 4, 0, Math.PI * 2);
    this.ctx.fill();

    this.ctx.restore();
  }

  _draw3DPlatform(p) {
    if (p.type === 'WALL') {
      // Solid boundary pillar
      this.ctx.fillStyle = '#1e293b';
      this.ctx.fillRect(p.x, p.y, p.w, p.h);
      this.ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(p.x, p.y, p.w, p.h);
      return;
    }

    // Platform block drop shadow
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    this.ctx.fillRect(p.x + 3, p.y + 3, p.w, p.h);

    // Platform surface gradient
    const platGrad = this.ctx.createLinearGradient(p.x, p.y, p.x, p.y + p.h);
    if (p.type === 'FLOOR') {
      platGrad.addColorStop(0, '#10b981');
      platGrad.addColorStop(0.18, '#047857');
      platGrad.addColorStop(1, '#064e3b');
    } else {
      platGrad.addColorStop(0, '#38bdf8');
      platGrad.addColorStop(0.2, '#0284c7');
      platGrad.addColorStop(1, '#0369a1');
    }
    this.ctx.fillStyle = platGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(p.x, p.y, p.w, p.h, 4);
    this.ctx.fill();

    // Top Specular Highlight Bevel
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
    this.ctx.fillRect(p.x + 2, p.y + 1, p.w - 4, 2);
  }

  _draw3DJumpPad(jp) {
    // Springboard base
    this.ctx.fillStyle = '#475569';
    this.ctx.fillRect(jp.x, jp.y + 4, jp.w, jp.h - 4);

    // High-bounce rubber pad (Glowing Red)
    const padGrad = this.ctx.createLinearGradient(jp.x, jp.y, jp.x, jp.y + jp.h);
    padGrad.addColorStop(0, '#f43f5e');
    padGrad.addColorStop(1, '#be123c');
    this.ctx.fillStyle = padGrad;
    this.ctx.beginPath();
    this.ctx.roundRect(jp.x, jp.y, jp.w, 5, 2);
    this.ctx.fill();

    // Chevrons pointing UP
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '700 8px monospace';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('▲▲ JUMP ▲▲', jp.x + jp.w / 2, jp.y + 4);
  }

  _draw3DHoop(hoop) {
    const isColl = hoop.collected;
    const ringColor = isColl ? '#10b981' : '#f59e0b';
    const innerColor = isColl ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)';

    // Glowing aura
    this.ctx.fillStyle = innerColor;
    this.ctx.beginPath();
    this.ctx.arc(hoop.x, hoop.y, hoop.radius, 0, Math.PI * 2);
    this.ctx.fill();

    // Golden 3D Ring
    this.ctx.strokeStyle = ringColor;
    this.ctx.lineWidth = 4.5;
    this.ctx.shadowColor = ringColor;
    this.ctx.shadowBlur = isColl ? 10 : 6;
    this.ctx.beginPath();
    this.ctx.arc(hoop.x, hoop.y, hoop.radius, 0, Math.PI * 2);
    this.ctx.stroke();
    this.ctx.shadowBlur = 0;

    // Specular highlight dot on top-left of ring
    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(hoop.x - hoop.radius * 0.7, hoop.y - hoop.radius * 0.7, 2.5, 0, Math.PI * 2);
    this.ctx.fill();
  }

  _draw3DSpike(s) {
    const spikeGrad = this.ctx.createLinearGradient(s.x, s.y, s.x + s.w, s.y + s.h);
    spikeGrad.addColorStop(0, '#f87171');
    spikeGrad.addColorStop(0.5, '#dc2626');
    spikeGrad.addColorStop(1, '#7f1d1d');
    this.ctx.fillStyle = spikeGrad;
    this.ctx.beginPath();
    this.ctx.moveTo(s.x, s.y + s.h);
    this.ctx.lineTo(s.x + s.w / 2, s.y);
    this.ctx.lineTo(s.x + s.w, s.y + s.h);
    this.ctx.closePath();
    this.ctx.fill();

    // Specular left bevel
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.45)';
    this.ctx.beginPath();
    this.ctx.moveTo(s.x, s.y + s.h);
    this.ctx.lineTo(s.x + s.w / 2, s.y);
    this.ctx.lineTo(s.x + s.w / 2, s.y + s.h);
    this.ctx.closePath();
    this.ctx.fill();
  }

  _draw3DGem(gem) {
    const r = 8;
    this.ctx.fillStyle = '#10b981';
    this.ctx.beginPath();
    this.ctx.moveTo(gem.x, gem.y - r);
    this.ctx.lineTo(gem.x + r, gem.y);
    this.ctx.lineTo(gem.x, gem.y + r);
    this.ctx.lineTo(gem.x - r, gem.y);
    this.ctx.closePath();
    this.ctx.fill();

    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(gem.x - 2, gem.y - 2, 2, 0, Math.PI * 2);
    this.ctx.fill();
  }

  _draw3DPortal(portal) {
    const unlocked = portal.unlocked;
    const col = unlocked ? '#38bdf8' : '#e11d48';

    // Portal arch interior
    this.ctx.fillStyle = unlocked ? 'rgba(56, 189, 248, 0.35)' : 'rgba(225, 29, 72, 0.22)';
    this.ctx.beginPath();
    this.ctx.roundRect(portal.x, portal.y, portal.w, portal.h, 22);
    this.ctx.fill();

    // Portal glowing frame
    this.ctx.strokeStyle = col;
    this.ctx.lineWidth = 3.5;
    this.ctx.shadowColor = col;
    this.ctx.shadowBlur = unlocked ? 16 : 8;
    this.ctx.stroke();
    this.ctx.shadowBlur = 0;

    // Portal status label inside door
    this.ctx.fillStyle = '#ffffff';
    this.ctx.font = '800 11px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText(unlocked ? 'EXIT' : '🔒 LOCK', portal.x + portal.w / 2, portal.y + portal.h / 2 + 4);

    // Floating Informative Badge above portal
    const remainingHoops = this.totalHoops - this.collectedHoops;
    const badgeText = unlocked
      ? '✨ EXIT UNLOCKED! ENTER HERE ✨'
      : `🔒 LOCKED: NEED ${remainingHoops} MORE HOOPS`;

    this.ctx.font = '700 10px "Plus Jakarta Sans", sans-serif';
    const textWidth = this.ctx.measureText(badgeText).width;
    const badgeW = textWidth + 16;
    const badgeX = portal.x + portal.w / 2 - badgeW / 2;
    const badgeY = portal.y - 22;

    this.ctx.fillStyle = unlocked ? 'rgba(16, 185, 129, 0.95)' : 'rgba(225, 29, 72, 0.95)';
    this.ctx.beginPath();
    this.ctx.roundRect(badgeX, badgeY, badgeW, 18, 9);
    this.ctx.fill();

    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillText(badgeText, portal.x + portal.w / 2, badgeY + 12);
  }

  _drawHUD(w, h) {
    // 1. Lives Display
    this.ctx.fillStyle = '#f43f5e';
    this.ctx.font = '700 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'left';
    let hearts = '';
    for (let i = 0; i < this.lives; i++) hearts += '❤️ ';
    this.ctx.fillText(hearts, 12, 22);

    // 2. Hoops Counter Display
    const remainingHoops = this.totalHoops - this.collectedHoops;
    this.ctx.textAlign = 'right';
    this.ctx.font = '700 12px "Plus Jakarta Sans", sans-serif';

    if (this.portal && this.portal.unlocked) {
      this.ctx.fillStyle = '#10b981';
      this.ctx.fillText(`🏆 ALL HOOPS COLLECTED! EXIT IS OPEN!`, w - 12, 22);
    } else {
      this.ctx.fillStyle = '#f59e0b';
      this.ctx.fillText(`🟡 ${this.collectedHoops}/${this.totalHoops} HOOPS (Collect all to unlock Exit)`, w - 12, 22);
    }

    // 3. Proximity Guidance Banner when near locked portal
    if (this.nearLockedPortal && remainingHoops > 0) {
      this.ctx.save();
      const bannerText = `👈 EXIT IS LOCKED! Roll back left to collect ${remainingHoops} remaining Hoops!`;
      this.ctx.font = '800 12px "Plus Jakarta Sans", sans-serif';
      const bW = this.ctx.measureText(bannerText).width + 24;
      const bX = (w - bW) / 2;
      const bY = h - 56;

      this.ctx.fillStyle = 'rgba(225, 29, 72, 0.92)';
      this.ctx.beginPath();
      this.ctx.roundRect(bX, bY, bW, 28, 14);
      this.ctx.fill();

      this.ctx.strokeStyle = '#ffffff';
      this.ctx.lineWidth = 1.5;
      this.ctx.stroke();

      this.ctx.fillStyle = '#ffffff';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(bannerText, w / 2, bY + 18);
      this.ctx.restore();
    }
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" & collect all 6 Golden Hoops to unlock the Exit!', w / 2, h / 2);
  }
}
