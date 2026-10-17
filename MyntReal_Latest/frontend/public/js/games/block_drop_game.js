/**
 * Game B: Block Drop Puzzle Engine (DC Protocol Oct 2026)
 * Original falling-block matrix game with SRS rotation, line clearing,
 * ghost piece, next-piece preview, soft/hard drop, and responsive controls.
 */

class BlockDropGame {
  constructor(canvas, previewCanvas, framework) {
    this.canvas = canvas;
    this.previewCanvas = previewCanvas;
    this.ctx = canvas.getContext('2d');
    this.previewCtx = previewCanvas ? previewCanvas.getContext('2d') : null;
    this.framework = framework;

    this.cols = 10;
    this.rows = 20;
    this.tileSize = 20;

    this.grid = [];
    this.currentPiece = null;
    this.nextPiece = null;

    this.isRunning = false;
    this.isPaused = false;
    this.animFrameId = null;

    this.dropInterval = 800; // ms per gravity step
    this.lastDropTime = 0;
    this.totalLines = 0;

    this.flashingRows = [];
    this.flashStartTime = 0;

    // Piece definitions & color palette
    this.SHAPES = {
      I: { matrix: [[1, 1, 1, 1]], color: '#06b6d4' },
      O: { matrix: [[1, 1], [1, 1]], color: '#eab308' },
      T: { matrix: [[0, 1, 0], [1, 1, 1]], color: '#a855f7' },
      S: { matrix: [[0, 1, 1], [1, 1, 0]], color: '#10b981' },
      Z: { matrix: [[1, 1, 0], [0, 1, 1]], color: '#ef4444' },
      J: { matrix: [[1, 0, 0], [1, 1, 1]], color: '#3b82f6' },
      L: { matrix: [[0, 0, 1], [1, 1, 1]], color: '#f97316' }
    };
    this.PIECE_KEYS = Object.keys(this.SHAPES);

    this._bindControls();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  resizeCanvas() {
    if (!this.canvas || !this.canvas.parentElement) return;
    const parentH = Math.min(window.innerHeight * 0.55, 520);
    const calculatedTile = Math.floor(parentH / this.rows);
    this.tileSize = Math.max(16, Math.min(26, calculatedTile));

    this.canvas.width = this.cols * this.tileSize;
    this.canvas.height = this.rows * this.tileSize;

    if (this.previewCanvas) {
      this.previewCanvas.width = 80;
      this.previewCanvas.height = 80;
    }

    if (!this.isRunning) this._drawIdle();
  }

  _bindControls() {
    window.addEventListener('keydown', (e) => {
      if (!this.isRunning || this.isPaused || !this.currentPiece) return;

      switch (e.code) {
        case 'ArrowLeft':
        case 'KeyA':
          this.moveLeft();
          break;
        case 'ArrowRight':
        case 'KeyD':
          this.moveRight();
          break;
        case 'ArrowUp':
        case 'KeyW':
          this.rotate();
          break;
        case 'ArrowDown':
        case 'KeyS':
          this.softDrop();
          break;
        case 'Space':
          this.hardDrop();
          break;
      }
    });

    // Mouse Pointer & Touch Canvas Controls
    let pointerStartX = 0;
    let pointerStartY = 0;
    let pointerStartTime = 0;
    let hasMovedPiece = false;

    this.canvas.addEventListener('pointerdown', (e) => {
      if (!this.isRunning || this.isPaused || !this.currentPiece) return;
      pointerStartX = e.clientX;
      pointerStartY = e.clientY;
      pointerStartTime = performance.now();
      hasMovedPiece = false;

      // Right click rotates
      if (e.button === 2) {
        e.preventDefault();
        this.rotate();
      }
    });

    window.addEventListener('pointermove', (e) => {
      if (!this.isRunning || this.isPaused || !this.currentPiece || pointerStartTime === 0) return;
      const dx = e.clientX - pointerStartX;
      const dy = e.clientY - pointerStartY;

      // Drag left/right to move piece horizontally
      const stepDist = this.tileSize * 0.85;
      if (Math.abs(dx) > stepDist) {
        if (dx > 0) this.moveRight();
        else this.moveLeft();
        pointerStartX = e.clientX;
        hasMovedPiece = true;
      }

      // Drag down to soft drop
      if (dy > stepDist * 1.4) {
        this.softDrop();
        pointerStartY = e.clientY;
        hasMovedPiece = true;
      }
    });

    window.addEventListener('pointerup', (e) => {
      if (!this.isRunning || this.isPaused || !this.currentPiece || pointerStartTime === 0) {
        pointerStartTime = 0;
        return;
      }
      const duration = performance.now() - pointerStartTime;
      const totalDx = e.clientX - pointerStartX;
      const totalDy = e.clientY - pointerStartY;
      pointerStartTime = 0;

      // Tap / click without drag: zone-based control
      if (!hasMovedPiece && duration < 350 && Math.hypot(totalDx, totalDy) < 20) {
        const rect = this.canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        const relX = clickX / rect.width;
        const relY = clickY / rect.height;

        if (relY > 0.75) {
          // Bottom area = soft drop
          this.softDrop();
        } else if (relX < 0.35) {
          // Left third = move left
          this.moveLeft();
        } else if (relX > 0.65) {
          // Right third = move right
          this.moveRight();
        } else {
          // Center / upper area = rotate
          this.rotate();
        }
      }
    });

    // Mouse wheel down to soft drop, wheel up to rotate
    this.canvas.addEventListener('wheel', (e) => {
      if (!this.isRunning || this.isPaused || !this.currentPiece) return;
      if (e.deltaY > 20) {
        this.softDrop();
      } else if (e.deltaY < -20) {
        this.rotate();
      }
    }, { passive: true });

    this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  }

  // Directional actions for mobile/keyboard
  moveLeft() {
    if (!this._collides(this.currentPiece.matrix, this.currentPiece.x - 1, this.currentPiece.y)) {
      this.currentPiece.x--;
    }
  }

  moveRight() {
    if (!this._collides(this.currentPiece.matrix, this.currentPiece.x + 1, this.currentPiece.y)) {
      this.currentPiece.x++;
    }
  }

  rotate() {
    const rotated = this._rotateMatrix(this.currentPiece.matrix);
    // Standard wall-kick offsets
    const kicks = [0, 1, -1, 2, -2];
    for (let k of kicks) {
      if (!this._collides(rotated, this.currentPiece.x + k, this.currentPiece.y)) {
        this.currentPiece.matrix = rotated;
        this.currentPiece.x += k;
        if (window.gameAudio) window.gameAudio.playRotate();
        return;
      }
    }
  }

  softDrop() {
    if (!this._collides(this.currentPiece.matrix, this.currentPiece.x, this.currentPiece.y + 1)) {
      this.currentPiece.y++;
      this.framework.addScore(1);
    }
  }

  hardDrop() {
    let cells = 0;
    while (!this._collides(this.currentPiece.matrix, this.currentPiece.x, this.currentPiece.y + 1)) {
      this.currentPiece.y++;
      cells++;
    }
    this.framework.addScore(cells * 2);
    if (window.gameAudio) window.gameAudio.playDrop();
    this._lockPiece();
  }

  start() {
    this.reset();
    this.isRunning = true;
    this.isPaused = false;
    this.lastDropTime = performance.now();

    this.nextPiece = this._randomPiece();
    this._spawnPiece();
    this._loop();
  }

  pause() {
    this.isPaused = true;
  }

  resume() {
    this.isPaused = false;
    this.lastDropTime = performance.now();
    this._loop();
  }

  reset() {
    this.isRunning = false;
    this.isPaused = false;
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    this.grid = Array.from({ length: this.rows }, () => Array(this.cols).fill(0));
    this.currentPiece = null;
    this.nextPiece = null;
    this.totalLines = 0;
    this.dropInterval = 800;
    this.flashingRows = [];
  }

  _randomPiece() {
    const key = this.PIECE_KEYS[Math.floor(Math.random() * this.PIECE_KEYS.length)];
    const shape = this.SHAPES[key];
    return {
      type: key,
      matrix: shape.matrix.map(row => [...row]),
      color: shape.color
    };
  }

  _spawnPiece() {
    this.currentPiece = this.nextPiece || this._randomPiece();
    this.nextPiece = this._randomPiece();
    this._drawPreview();

    this.currentPiece.x = Math.floor((this.cols - this.currentPiece.matrix[0].length) / 2);
    this.currentPiece.y = 0;

    // Game over if new piece immediately collides
    if (this._collides(this.currentPiece.matrix, this.currentPiece.x, this.currentPiece.y)) {
      this._handleGameOver();
    }
  }

  _rotateMatrix(matrix) {
    const H = matrix.length;
    const W = matrix[0].length;
    const result = Array.from({ length: W }, () => Array(H).fill(0));
    for (let r = 0; r < H; r++) {
      for (let c = 0; c < W; c++) {
        result[c][H - 1 - r] = matrix[r][c];
      }
    }
    return result;
  }

  _collides(matrix, px, py) {
    for (let r = 0; r < matrix.length; r++) {
      for (let c = 0; c < matrix[r].length; c++) {
        if (matrix[r][c] !== 0) {
          const gx = px + c;
          const gy = py + r;
          if (gx < 0 || gx >= this.cols || gy >= this.rows) return true;
          if (gy >= 0 && this.grid[gy][gx] !== 0) return true;
        }
      }
    }
    return false;
  }

  _lockPiece() {
    const matrix = this.currentPiece.matrix;
    for (let r = 0; r < matrix.length; r++) {
      for (let c = 0; c < matrix[r].length; c++) {
        if (matrix[r][c] !== 0) {
          const gy = this.currentPiece.y + r;
          const gx = this.currentPiece.x + c;
          if (gy >= 0 && gy < this.rows && gx >= 0 && gx < this.cols) {
            this.grid[gy][gx] = this.currentPiece.color;
          }
        }
      }
    }

    this._checkLines();
    this._spawnPiece();
  }

  _checkLines() {
    const fullRows = [];
    for (let r = this.rows - 1; r >= 0; r--) {
      if (this.grid[r].every(cell => cell !== 0)) {
        fullRows.push(r);
      }
    }

    if (fullRows.length > 0) {
      if (window.gameAudio) window.gameAudio.playLineClear();

      // Line score multipliers
      const scoreTable = { 1: 100, 2: 300, 3: 500, 4: 800 };
      const pts = scoreTable[fullRows.length] || 1000;
      this.framework.addScore(pts);

      this.totalLines += fullRows.length;
      this.framework.setLines(this.totalLines);

      // Level progression every 4 lines cleared
      const lvl = Math.floor(this.totalLines / 4) + 1;
      this.framework.setLevel(lvl);
      this.dropInterval = Math.max(120, 800 - ((lvl - 1) * 70));

      if (this.totalLines % 4 === 0) {
        this.framework.recordMilestone(this.totalLines);
      }

      // Remove lines and pull grid downward
      for (let r of fullRows) {
        this.grid.splice(r, 1);
        this.grid.unshift(Array(this.cols).fill(0));
      }
    }
  }

  _loop(timestamp = 0) {
    if (!this.isRunning || this.isPaused) return;

    if (timestamp - this.lastDropTime >= this.dropInterval) {
      if (this.currentPiece) {
        if (!this._collides(this.currentPiece.matrix, this.currentPiece.x, this.currentPiece.y + 1)) {
          this.currentPiece.y++;
        } else {
          this._lockPiece();
        }
      }
      this.lastDropTime = timestamp;
    }

    this._draw();
    this.animFrameId = requestAnimationFrame((t) => this._loop(t));
  }

  _handleGameOver() {
    this.isRunning = false;
    if (window.gameAudio) window.gameAudio.playCollision();
    this.framework.gameOver({
      score: this.framework.score,
      linesCleared: this.totalLines,
      level: this.framework.level
    });
  }

  _getGhostY() {
    if (!this.currentPiece) return 0;
    let gy = this.currentPiece.y;
    while (!this._collides(this.currentPiece.matrix, this.currentPiece.x, gy + 1)) {
      gy++;
    }
    return gy;
  }

  _draw() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const ts = this.tileSize;

    // Background
    this.ctx.fillStyle = '#090e17';
    this.ctx.fillRect(0, 0, w, h);

    // Grid lines
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.04)';
    this.ctx.lineWidth = 1;
    for (let c = 0; c <= this.cols; c++) {
      this.ctx.beginPath();
      this.ctx.moveTo(c * ts, 0);
      this.ctx.lineTo(c * ts, h);
      this.ctx.stroke();
    }
    for (let r = 0; r <= this.rows; r++) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, r * ts);
      this.ctx.lineTo(w, r * ts);
      this.ctx.stroke();
    }

    // Settled blocks in grid
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        if (this.grid[r][c] !== 0) {
          this._drawBlock(c * ts, r * ts, ts, this.grid[r][c]);
        }
      }
    }

    // Ghost piece
    if (this.currentPiece) {
      const ghostY = this._getGhostY();
      const m = this.currentPiece.matrix;
      for (let r = 0; r < m.length; r++) {
        for (let c = 0; c < m[r].length; c++) {
          if (m[r][c] !== 0) {
            const gx = (this.currentPiece.x + c) * ts;
            const gy = (ghostY + r) * ts;
            this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
            this.ctx.lineWidth = 1.5;
            this.ctx.strokeRect(gx + 1, gy + 1, ts - 2, ts - 2);
          }
        }
      }

      // Active falling piece
      for (let r = 0; r < m.length; r++) {
        for (let c = 0; c < m[r].length; c++) {
          if (m[r][c] !== 0) {
            const bx = (this.currentPiece.x + c) * ts;
            const by = (this.currentPiece.y + r) * ts;
            this._drawBlock(bx, by, ts, this.currentPiece.color);
          }
        }
      }
    }
  }

  _drawBlock(x, y, size, color) {
    this.ctx.fillStyle = color;
    this.ctx.beginPath();
    this.ctx.roundRect(x + 1, y + 1, size - 2, size - 2, 3);
    this.ctx.fill();

    // Top-left highlight bevel
    this.ctx.fillStyle = 'rgba(255, 255, 255, 0.28)';
    this.ctx.fillRect(x + 2, y + 2, size - 4, 2);
    this.ctx.fillRect(x + 2, y + 2, 2, size - 4);

    // Bottom-right shadow bevel
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.35)';
    this.ctx.fillRect(x + size - 3, y + 2, 2, size - 4);
    this.ctx.fillRect(x + 2, y + size - 3, size - 4, 2);
  }

  _drawPreview() {
    if (!this.previewCtx || !this.nextPiece) return;
    const pw = this.previewCanvas.width;
    const ph = this.previewCanvas.height;

    this.previewCtx.fillStyle = '#0f172a';
    this.previewCtx.fillRect(0, 0, pw, ph);

    const m = this.nextPiece.matrix;
    const pTile = 16;
    const offX = Math.floor((pw - (m[0].length * pTile)) / 2);
    const offY = Math.floor((ph - (m.length * pTile)) / 2);

    for (let r = 0; r < m.length; r++) {
      for (let c = 0; c < m[r].length; c++) {
        if (m[r][c] !== 0) {
          const bx = offX + c * pTile;
          const by = offY + r * pTile;
          this.previewCtx.fillStyle = this.nextPiece.color;
          this.previewCtx.beginPath();
          this.previewCtx.roundRect(bx + 1, by + 1, pTile - 2, pTile - 2, 2);
          this.previewCtx.fill();
        }
      }
    }
  }

  _drawIdle() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.fillStyle = '#090e17';
    this.ctx.fillRect(0, 0, w, h);

    this.ctx.fillStyle = '#94a3b8';
    this.ctx.font = '600 13px "Plus Jakarta Sans", sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.fillText('Press "Start Game" to drop blocks', w / 2, h / 2);
  }
}
