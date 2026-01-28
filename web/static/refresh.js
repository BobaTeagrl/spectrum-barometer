setInterval(() => {
    const img = document.querySelector("img");
    img.src = "/graph/pressure.png?ts=" + Date.now();
  }, 60000);
  