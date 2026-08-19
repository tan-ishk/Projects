#include "tetrisboard.h"
#include <QPainter>
#include <QKeyEvent>
#include <QTimerEvent>
#include <QTime>
#include <cstdlib>

TetrisBoard::TetrisBoard(QWidget *parent)
    : QWidget(parent),
      cellSize(28),
      board(BoardWidth * BoardHeight, 0),
      currentType(0),
      currentRotation(0),
      currentPos(0,0),
      timerId(0),
      dropIntervalMs(500),
      paused(false),
      score(0)
{
    setWindowTitle("Tetris - Qt Minimal");
    setFixedSize(BoardWidth * cellSize + 2, BoardHeight * cellSize + 2);

    // Colors for 7 tetrominoes (index 1..7)
    colors.resize(8);
    colors[0] = QColor(0,0,0); // empty
    colors[1] = QColor(0, 180, 255); // I
    colors[2] = QColor(0, 200, 0); // S
    colors[3] = QColor(255, 150, 0); // Z
    colors[4] = QColor(200, 0, 200); // T
    colors[5] = QColor(255, 220, 0); // O
    colors[6] = QColor(120, 120, 255); // J
    colors[7] = QColor(255, 100, 100); // L

    initShapes();
    srand(static_cast<unsigned>(QTime::currentTime().msec()));
    spawnPiece();
    timerId = startTimer(dropIntervalMs);
}

QSize TetrisBoard::sizeHint() const
{
    return QSize(BoardWidth * cellSize, BoardHeight * cellSize);
}

void TetrisBoard::initShapes()
{
    // We'll define each tetromino as 4 rotations, each rotation is 4 QPoint offsets (x,y)
    // Coordinates are relative to a 4x4 block with origin at top-left.

    // I (cyan) - horizontal line
    pieces[0].resize(4);
    pieces[0][0] = { {0,1},{1,1},{2,1},{3,1} };
    pieces[0][1] = { {2,0},{2,1},{2,2},{2,3} };
    pieces[0][2] = pieces[0][0];
    pieces[0][3] = pieces[0][1];

    // S (green)
    pieces[1].resize(4);
    pieces[1][0] = { {1,1},{2,1},{0,2},{1,2} };
    pieces[1][1] = { {1,0},{1,1},{2,1},{2,2} };
    pieces[1][2] = pieces[1][0];
    pieces[1][3] = pieces[1][1];

    // Z (orange-red)
    pieces[2].resize(4);
    pieces[2][0] = { {0,1},{1,1},{1,2},{2,2} };
    pieces[2][1] = { {2,0},{1,1},{2,1},{1,2} };
    pieces[2][2] = pieces[2][0];
    pieces[2][3] = pieces[2][1];

    // T (purple)
    pieces[3].resize(4);
    pieces[3][0] = { {1,1},{0,2},{1,2},{2,2} };
    pieces[3][1] = { {1,0},{1,1},{2,1},{1,2} };
    pieces[3][2] = { {0,1},{1,1},{2,1},{1,2} };
    pieces[3][3] = { {1,0},{0,1},{1,1},{1,2} };

    // O (yellow) square
    pieces[4].resize(4);
    pieces[4][0] = { {1,1},{2,1},{1,2},{2,2} };
    pieces[4][1] = pieces[4][0];
    pieces[4][2] = pieces[4][0];
    pieces[4][3] = pieces[4][0];

    // J (blue)
    pieces[5].resize(4);
    pieces[5][0] = { {0,1},{0,2},{1,2},{2,2} };
    pieces[5][1] = { {1,0},{2,0},{1,1},{1,2} };
    pieces[5][2] = { {0,1},{1,1},{2,1},{2,2} };
    pieces[5][3] = { {1,0},{1,1},{1,2},{0,2} };

    // L (red)
    pieces[6].resize(4);
    pieces[6][0] = { {2,1},{0,2},{1,2},{2,2} };
    pieces[6][1] = { {1,0},{1,1},{1,2},{2,2} };
    pieces[6][2] = { {0,1},{1,1},{2,1},{0,2} };
    pieces[6][3] = { {0,0},{1,0},{1,1},{1,2} };
}

QVector<QPoint> TetrisBoard::shapeCoords(int type, int rotation) const
{
    // type 0..6 maps to pieces index 0..6, but board stores 1..7 for colors
    QVector<QPoint> coords = pieces[type][rotation % pieces[type].size()];
    return coords;
}

bool TetrisBoard::isCollision(const QPoint &pos, const QVector<QPoint> &coords) const
{
    for (const QPoint &p : coords) {
        int x = pos.x() + p.x();
        int y = pos.y() + p.y();
        if (x < 0 || x >= BoardWidth || y < 0 || y >= BoardHeight) return true;
        if (board[y * BoardWidth + x] != 0) return true;
    }
    return false;
}

bool TetrisBoard::tryMove(int dx, int dy, int newRotation)
{
    QPoint newPos = currentPos + QPoint(dx, dy);
    QVector<QPoint> coords = shapeCoords(currentType, newRotation);
    if (!isCollision(newPos, coords)) {
        currentPos = newPos;
        currentRotation = newRotation % pieces[currentType].size();
        update();
        return true;
    }
    return false;
}

void TetrisBoard::placePiece()
{
    QVector<QPoint> coords = shapeCoords(currentType, currentRotation);
    for (const QPoint &p : coords) {
        int x = currentPos.x() + p.x();
        int y = currentPos.y() + p.y();
        if (y >= 0 && y < BoardHeight && x >= 0 && x < BoardWidth)
            board[y * BoardWidth + x] = currentType + 1; // color index
    }
    clearLines();
    spawnPiece();
}

void TetrisBoard::clearLines()
{
    int linesCleared = 0;
    for (int y = BoardHeight - 1; y >= 0; --y) {
        bool full = true;
        for (int x = 0; x < BoardWidth; ++x) {
            if (board[y * BoardWidth + x] == 0) { full = false; break; }
        }
        if (full) {
            ++linesCleared;
            // move everything above down
            for (int yy = y; yy > 0; --yy) {
                for (int x = 0; x < BoardWidth; ++x) {
                    board[yy * BoardWidth + x] = board[(yy - 1) * BoardWidth + x];
                }
            }
            // clear top row
            for (int x = 0; x < BoardWidth; ++x) board[x] = 0;
            ++y; // recheck same row index after shift
        }
    }
    if (linesCleared > 0) {
        score += linesCleared * 100;
        // optionally speed up
        dropIntervalMs = qMax(50, dropIntervalMs - linesCleared * 10);
        killTimer(timerId);
        timerId = startTimer(dropIntervalMs);
    }
}

void TetrisBoard::spawnPiece()
{
    currentType = rand() % 7;
    currentRotation = 0;
    // initial position such that 4x4 matrix top-left aligns
    currentPos = QPoint(BoardWidth/2 - 2, 0);
    if (isCollision(currentPos, shapeCoords(currentType, currentRotation))) {
        // game over -> reset
        resetGame();
    }
    update();
}

void TetrisBoard::resetGame()
{
    board.fill(0);
    score = 0;
    dropIntervalMs = 500;
    killTimer(timerId);
    timerId = startTimer(dropIntervalMs);
}

void TetrisBoard::hardDrop()
{
    while (tryMove(0, 1, currentRotation)) {}
    placePiece();
}

void TetrisBoard::timerEvent(QTimerEvent *event)
{
    Q_UNUSED(event);
    if (paused) return;
    if (!tryMove(0, 1, currentRotation)) {
        placePiece();
    }
}

void TetrisBoard::keyPressEvent(QKeyEvent *event)
{
    if (event->key() == Qt::Key_P) {
        paused = !paused;
        return;
    }
    if (paused) return;

    switch (event->key()) {
    case Qt::Key_Left:
        tryMove(-1, 0, currentRotation);
        break;
    case Qt::Key_Right:
        tryMove(1, 0, currentRotation);
        break;
    case Qt::Key_Down:
        tryMove(0, 1, currentRotation);
        break;
    case Qt::Key_Up:
    case Qt::Key_X:
        tryMove(0, 0, (currentRotation + 1) % 4);
        break;
    case Qt::Key_Z:
        tryMove(0, 0, (currentRotation + 3) % 4);
        break;
    case Qt::Key_Space:
        hardDrop();
        break;
    default:
        QWidget::keyPressEvent(event);
    }
}

void TetrisBoard::paintEvent(QPaintEvent * /*event*/)
{
    QPainter painter(this);
    painter.fillRect(rect(), Qt::black);

    // draw board squares
    for (int y = 0; y < BoardHeight; ++y) {
        for (int x = 0; x < BoardWidth; ++x) {
            int val = board[y * BoardWidth + x];
            QRect r(x * cellSize + 1, y * cellSize + 1, cellSize - 2, cellSize - 2);
            if (val != 0) {
                painter.fillRect(r, colors[val]);
                painter.drawRect(r);
            } else {
                painter.setPen(QColor(50,50,50));
                painter.drawRect(r);
            }
        }
    }

    // draw current piece
    QVector<QPoint> coords = shapeCoords(currentType, currentRotation);
    for (const QPoint &p : coords) {
        int x = currentPos.x() + p.x();
        int y = currentPos.y() + p.y();
        if (y >= 0) {
            QRect r(x * cellSize + 1, y * cellSize + 1, cellSize - 2, cellSize - 2);
            painter.fillRect(r, colors[currentType + 1]);
            painter.drawRect(r);
        }
    }

    // draw score
    painter.setPen(Qt::white);
    painter.drawText(6, 12, QString("Score: %1").arg(score));
}
