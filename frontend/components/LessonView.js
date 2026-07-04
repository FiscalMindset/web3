"use client";
import Markdown from "./Markdown";

export default function LessonView({ lesson, sessionId, onAskTutor, onRan }) {
  if (!lesson) return null;
  return (
    <div className="lesson-scroll">
      <div className="lesson-inner">
        <div className="lesson-top">
          <span className="badge">{lesson.module}</span>
          <span>~{lesson.minutes} min</span>
          <span style={{ flex: 1 }} />
          <button
            className="btn amber"
            onClick={() =>
              onAskTutor(
                null,
                null,
                `I'm reading the lesson "${lesson.title}". Quiz me with one question to check I understood it, then we discuss.`
              )
            }
          >
            ✦ quiz me on this lesson
          </button>
        </div>
        <Markdown sessionId={sessionId} onAskTutor={onAskTutor} onRan={onRan}>
          {lesson.body}
        </Markdown>
      </div>
    </div>
  );
}
