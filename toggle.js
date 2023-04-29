function toggleState(obj) {
    if (obj.className == 'bingo_sq inactive') {
	obj.className = 'bingo_sq active';
    } else if (obj.className == 'bingo_sq active') {
	obj.className = 'bingo_sq blocked';
    } else if (obj.className == 'bingo_sq blocked') {
	obj.className = 'bingo_sq inactive';
    } else {
	prop.className = 'bingo_sq inactive';
    }
}

function incCounterDeaths(inc) {
    cnt = document.getElementById("death_counter");
    var val = parseInt(cnt.textContent);
    val = inc ? val + 1 : val - 1;
    val = Math.max(val, 0);
    cnt.textContent = val.toString();
}

function incCounterMIAB(inc) {
    cnt = document.getElementById("miab_counter");
    var val = parseInt(cnt.textContent);
    val = inc ? val + 1 : val - 1;
    val = Math.max(val, 0);
    cnt.textContent = val.toString();
}
