let currentQuestion = null;

let score = 0;
let wrong = 0;

async function loadQuestion() {

    const response = await fetch("/random_question");

    currentQuestion = await response.json();

    showQuestion();
}

async function loadAIQuestion() {

    const response = await fetch("/generate_ai_question");

    currentQuestion = await response.json();

    showQuestion();
}

function showQuestion() {

    document.getElementById("difficulty").innerText =
        "Difficulty: " + currentQuestion.difficulty;

    document.getElementById("category").innerText =
        "Category: " + currentQuestion.category;

    document.getElementById("question").innerText =
        currentQuestion.question_text;

    document.getElementById("A").innerText =
        "A. " + currentQuestion.option_a;

    document.getElementById("B").innerText =
        "B. " + currentQuestion.option_b;

    document.getElementById("C").innerText =
        "C. " + currentQuestion.option_c;

    document.getElementById("D").innerText =
        "D. " + currentQuestion.option_d;

    
    document.getElementById("result").innerHTML = "";
}


async function checkAnswer(selected) {

    const correct = currentQuestion.correct_option;

    if (selected === correct) {
        score++;
        document.getElementById("result").innerHTML = "✅ Correct!";
    } else {
        wrong++;
        document.getElementById("result").innerHTML = 
            `❌ Wrong! Correct answer: ${correct}`;

        // Get AI Explanation
        try {
            const response = await fetch("/explain_answer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: currentQuestion.question_text,
                    correct: correct,
                    selected: selected
                })
            });

            const data = await response.json();
            document.getElementById("result").innerHTML += 
                `<br><br>🤖 ${data.explanation}`;
        } catch (err) {
            console.error("Explanation fetch failed", err);
        }
    }

    // Update Score
    document.getElementById("score").innerHTML = 
        `✅ Correct: ${score} | ❌ Wrong: ${wrong}`;
}

// Optional: Reset score button (add this if you want)
function resetScore() {
    score = 0;
    wrong = 0;
    document.getElementById("score").innerHTML = `✅ Correct: 0 | ❌ Wrong: 0`;
}