(() => {
  "use strict";
  const canvas = document.getElementById("snake-board");
  const ctx = canvas.getContext("2d");
  const scoreLabel = document.getElementById("score-label");
  const status = document.getElementById("game-status");
  const size = 24, cells = canvas.width / size;
  const directions = {
    up: {x:0,y:-1}, down:{x:0,y:1}, left:{x:-1,y:0}, right:{x:1,y:0}
  };
  let snake, direction, nextDirection, food, score, timer, running = false, ended = false;

  function randomFood() {
    let candidate;
    do {
      candidate = {x:Math.floor(Math.random()*cells), y:Math.floor(Math.random()*cells)};
    } while (snake.some(part => part.x===candidate.x && part.y===candidate.y));
    return candidate;
  }
  function draw() {
    ctx.fillStyle = "#032b40"; ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.strokeStyle = "#0a4864"; ctx.lineWidth = 1;
    for (let i=0;i<=cells;i++) {
      ctx.beginPath(); ctx.moveTo(i*size,0); ctx.lineTo(i*size,canvas.height); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0,i*size); ctx.lineTo(canvas.width,i*size); ctx.stroke();
    }
    if (food) { ctx.fillStyle="#00d985"; ctx.fillRect(food.x*size+3,food.y*size+3,size-6,size-6); }
    snake?.forEach((part,index) => {
      ctx.fillStyle = index===0 ? "#7fe3ff" : "#0082ba";
      ctx.fillRect(part.x*size+2,part.y*size+2,size-4,size-4);
    });
  }
  function update() {
    direction = nextDirection;
    const head = {x:snake[0].x+direction.x,y:snake[0].y+direction.y};
    if (head.x<0 || head.y<0 || head.x>=cells || head.y>=cells ||
        snake.some((part,index) => index>0 && part.x===head.x && part.y===head.y)) {
      stop(); ended=true; status.textContent=`Game over — score: ${score}. Press Start / Restart to try again.`; return;
    }
    snake.unshift(head);
    if (head.x===food.x && head.y===food.y) {
      score++; scoreLabel.textContent=`Score: ${score}`; food=randomFood();
    } else snake.pop();
    draw();
  }
  function start() {
    clearInterval(timer);
    snake=[{x:10,y:10},{x:9,y:10},{x:8,y:10}];
    direction=directions.right; nextDirection=directions.right;
    score=0; scoreLabel.textContent="Score: 0"; food=randomFood();
    running=true; ended=false; status.textContent="Game on!";
    draw(); timer=setInterval(update,115);
  }
  function stop() { clearInterval(timer); running=false; }
  function turn(name) {
    const candidate=directions[name];
    if (!candidate || !running) return;
    if (candidate.x===-direction.x && candidate.y===-direction.y) return;
    nextDirection=candidate;
  }
  document.getElementById("start-game").addEventListener("click",start);
  document.getElementById("pause-game").addEventListener("click",() => {
    if (running) { stop(); status.textContent="Paused."; }
    else if (snake && !ended) { running=true; timer=setInterval(update,115); status.textContent="Game on!"; }
  });
  document.querySelectorAll("[data-dir]").forEach(button => button.addEventListener("click",() => turn(button.dataset.dir)));
  document.addEventListener("keydown",event => {
    const keys={ArrowUp:"up",w:"up",W:"up",ArrowDown:"down",s:"down",S:"down",
      ArrowLeft:"left",a:"left",A:"left",ArrowRight:"right",d:"right",D:"right"};
    const move=keys[event.key];
    if (move) { event.preventDefault(); turn(move); }
  });
  draw();
})();
