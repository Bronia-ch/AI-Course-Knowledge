/**
 * 学习统计概览
 */
export function calculateLearningStats(courses) {
  const stats = courses.reduce(
    (result, course) => {
      const lessonCount = course.total_lessons || 0;
      result.totalLessons += lessonCount;
      result.completedLessons += course.completed_lessons || 0;
      result.weightedProgress += (course.progress_percent || 0) * lessonCount;

      if (course.learning_status === "in_progress") {
        result.inProgressCourses += 1;
      } else if (course.learning_status === "completed") {
        result.completedCourses += 1;
      }
      return result;
    },
    {
      totalLessons: 0,
      completedLessons: 0,
      inProgressCourses: 0,
      completedCourses: 0,
      weightedProgress: 0,
    },
  );

  const overallProgress = stats.totalLessons > 0
    ? stats.weightedProgress / stats.totalLessons
    : 0;

  return { ...stats, overallProgress };
}

export default function LearningStats({ courses }) {
  const stats = calculateLearningStats(courses);

  const items = [
    { label: "课程总数", value: courses.length },
    { label: "学习中", value: stats.inProgressCourses },
    { label: "已完成课程", value: stats.completedCourses },
    {
      label: "已完成课节",
      value: `${stats.completedLessons}/${stats.totalLessons}`,
    },
    { label: "总体进度", value: `${stats.overallProgress.toFixed(1)}%` },
  ];

  return (
    <section className="learning-stats" aria-label="学习统计">
      <h2>学习概览</h2>
      <div className="learning-stats-grid">
        {items.map((item) => (
          <div className="learning-stat-item" key={item.label}>
            <strong>{item.value}</strong>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      <div className="learning-stats-progress" aria-hidden="true">
        <div
          style={{
            width: `${Math.min(Math.max(stats.overallProgress, 0), 100)}%`,
          }}
        />
      </div>
    </section>
  );
}
