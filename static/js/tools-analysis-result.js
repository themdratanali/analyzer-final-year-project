
document.addEventListener("DOMContentLoaded", () => {
    const totalScore = Number(document.body.dataset.totalScore || 0);
    const circumference = 490;
    const offset = circumference - (circumference * totalScore) / 100;
    const progressCircle = document.querySelector(".score-orb-progress");

    if (progressCircle) {
        progressCircle.style.strokeDashoffset = String(circumference);
        setTimeout(() => {
            progressCircle.style.transition = "stroke-dashoffset 2.2s cubic-bezier(0.22, 1, 0.36, 1)";
            progressCircle.style.strokeDashoffset = String(offset);
        }, 100);
    }

    document.querySelectorAll(".progress-bar").forEach((el) => {
        const width = `${el.dataset.width || 0}%`;
        el.style.width = "0";
        setTimeout(() => {
            el.style.width = width;
        }, 150);
    });

    const sectionChart = document.getElementById("section-score-chart");
    if (sectionChart) {
        const scoreRows = Array.from(document.querySelectorAll(".score-item"));
        const bars = scoreRows.map((row) => {
            const labelNode = row.querySelector(".score-label span:first-child");
            const valueNode = row.querySelector(".score-label span:last-child");
            const label = labelNode ? labelNode.textContent.trim() : "Section";
            const pctMatch = valueNode ? valueNode.textContent.match(/\(([\d.]+)%\)/) : null;
            const value = pctMatch ? Number(pctMatch[1]) : 0;
            return { label, value };
        });
        drawSectionChart(sectionChart, bars);
    }

    const keywordBtn = document.getElementById("analyze-keywords");
    const keywordLoading = document.getElementById("keyword-loading");
    const keywordResult = document.getElementById("keyword-result");
    const keywordAdvancedResult = document.getElementById("keyword-advanced-result");
    const keywordError = document.getElementById("keyword-error");

    if (keywordBtn) {
        keywordBtn.addEventListener('click', async () => {
            const jobDescription = document.getElementById("job-description-input").value.trim();
            
            if (!jobDescription) {
                keywordError.textContent = "Please enter a job description.";
                keywordError.style.display = "block";
                return;
            }
            keywordError.style.display = "none";

            keywordLoading.style.display = 'block';
            keywordResult.style.display = 'none';
            if (keywordAdvancedResult) {
                keywordAdvancedResult.style.display = "none";
            }

            try {
                const response = await fetch("/api/resume/keyword-gap", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        resume_text: window.resumeText || "",
                        job_description: jobDescription
                    })
                });

                const data = await response.json();

                if (data.success && data.result) {
                    const matched = data.result.matched || [];
                    const missing = data.result.missing || [];

                    document.getElementById("matched-keywords").innerHTML = matched.length
                        ? matched.map((k) => `<li>${k}</li>`).join("")
                        : "<li>No matched keywords found</li>";
                    document.getElementById("missing-keywords").innerHTML = missing.length
                        ? missing.map((k) => `<li>${k}</li>`).join("")
                        : "<li>No missing keywords found</li>";

                    keywordResult.style.display = "grid";

                    if (keywordAdvancedResult && data.result && data.advanced) {
                        const stats = data.result.stats || {};
                        const components = (data.advanced && data.advanced.components) || {};

                        document.getElementById("keyword-stats").innerHTML = `
                            <li>Job Keywords: ${stats.job_keywords_total || 0}</li>
                            <li>Matched Keywords: ${stats.matched_count || 0}</li>
                            <li>Missing Keywords: ${stats.missing_count || 0}</li>
                            <li>Coverage: ${stats.coverage_pct || 0}%</li>
                            <li>Advanced Match Score: ${data.advanced.score || 0}%</li>
                        `;

                        document.getElementById("ensemble-components").innerHTML = `
                            <li>TF-IDF Word Similarity: ${components.tfidf_word_similarity || 0}%</li>
                            <li>TF-IDF Char Similarity: ${components.tfidf_char_similarity || 0}%</li>
                            <li>Bag-of-Words Similarity: ${components.bow_similarity || 0}%</li>
                            <li>SBERT Semantic Similarity: ${components.sbert_semantic_similarity || 0}%</li>
                            <li>Keyword Coverage Signal: ${components.keyword_coverage || 0}%</li>
                        `;
                        keywordAdvancedResult.style.display = "grid";
                    }
                } else {
                    keywordError.textContent = data.error || "Failed to analyze keywords";
                    keywordError.style.display = "block";
                }
            } catch (err) {
                keywordError.textContent = "Error connecting to server";
                keywordError.style.display = "block";
            } finally {
                keywordLoading.style.display = "none";
            }
        });
    }
});

function drawSectionChart(canvas, bars) {
    if (!canvas || !bars.length) {
        return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
        return;
    }

    const width = canvas.width;
    const height = canvas.height;
    const leftPad = 24;
    const rightPad = 16;
    const topPad = 10;
    const bottomPad = 36;
    const chartWidth = width - leftPad - rightPad;
    const chartHeight = height - topPad - bottomPad;
    const gap = 8;
    const barWidth = Math.max((chartWidth - (bars.length - 1) * gap) / bars.length, 12);

    ctx.clearRect(0, 0, width, height);
    ctx.font = "11px Inter";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    bars.forEach((bar, index) => {
        const barHeight = (Math.max(Math.min(bar.value, 100), 0) / 100) * chartHeight;
        const x = leftPad + index * (barWidth + gap);
        const y = topPad + (chartHeight - barHeight);

        const gradient = ctx.createLinearGradient(0, y, 0, topPad + chartHeight);
        gradient.addColorStop(0, "#5550FA");
        gradient.addColorStop(1, "#51DAFC");
        ctx.fillStyle = gradient;
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = "#312e81";
        ctx.fillText(`${Math.round(bar.value)}%`, x + (barWidth / 2), y - 8);

        const shortLabel = bar.label.length > 11 ? `${bar.label.slice(0, 10)}...` : bar.label;
        ctx.fillStyle = "#475569";
        ctx.fillText(shortLabel, x + (barWidth / 2), topPad + chartHeight + 12);
    });
}

window.resumeText = "";
window.resumeTextData = JSON.parse(document.getElementById('resume-text-data').textContent);
