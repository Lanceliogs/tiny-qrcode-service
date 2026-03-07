const $ = (s) => document.getElementById(s);

$("gradient-type").addEventListener("change", function () {
  $("gradient-end-wrap").hidden = this.value === "none";
});

const logoFile = $("logo-file");
const logoB64  = $("logo-b64");
const preview  = $("logo-preview");
const thumb    = $("logo-thumb");

logoFile.addEventListener("change", () => {
  const file = logoFile.files[0];
  if (!file) return;
  if (file.size > 1024 * 1024) {
    alert("Logo must be under 1 MB.");
    logoFile.value = "";
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    logoB64.value = reader.result.split(",")[1];
    thumb.src = reader.result;
    preview.hidden = false;
    logoFile.hidden = true;
  };
  reader.readAsDataURL(file);
});

$("logo-change").addEventListener("click", () => logoFile.click());

$("logo-remove").addEventListener("click", () => {
  logoB64.value = "";
  logoFile.value = "";
  preview.hidden = true;
  logoFile.hidden = false;
  thumb.removeAttribute("src");
});

$("box-size-range").addEventListener("input", function () {
  $("box-size-val").textContent = this.value;
});
$("border-range").addEventListener("input", function () {
  $("border-val").textContent = this.value;
});

const previewSection = document.querySelector(".preview");
if (previewSection) {
  previewSection.scrollIntoView({ behavior: "instant", block: "nearest" });
}
