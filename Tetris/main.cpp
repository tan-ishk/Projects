#include <QApplication>
#include "tetrisboard.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    TetrisBoard board;
    board.show();
    return app.exec();
}
