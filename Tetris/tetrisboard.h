#ifndef TETRISBOARD_H
#define TETRISBOARD_H

#include <QWidget>
#include <QVector>
#include <QColor>
#include <QPoint>

class TetrisBoard : public QWidget
{
    Q_OBJECT
public:
    explicit TetrisBoard(QWidget *parent = nullptr);
    QSize sizeHint() const override;
protected:
    void paintEvent(QPaintEvent *event) override;
    void keyPressEvent(QKeyEvent *event) override;
    void timerEvent(QTimerEvent *event) override;
private:
    static const int BoardWidth = 10;
    static const int BoardHeight = 20;
    int cellSize;
    QVector<int> board; // BoardWidth * BoardHeight: 0 empty, 1-7 colors
    QVector<QColor> colors;

    // Piece state
    int currentType; // 0..6
    int currentRotation; // 0..3
    QPoint currentPos; // top-left reference in board coords (x,y)

    // Each piece: vector of 4 rotations; each rotation = 4 QPoint offsets
    QVector<QVector<QPoint>> pieces[7];

    int timerId;
    int dropIntervalMs;
    bool paused;
    int score;

    void initShapes();
    QVector<QPoint> shapeCoords(int type, int rotation) const;
    bool isCollision(const QPoint &pos, const QVector<QPoint> &coords) const;
    bool tryMove(int dx, int dy, int newRotation);
    void placePiece();
    void clearLines();
    void spawnPiece();
    void hardDrop();
    void resetGame();
signals:
    void gameOver();
};

#endif // TETRISBOARD_H
