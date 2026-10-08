int escolher(bool b) {
    int x;
    if (b) {
        {
            {
                x = 10;
            }
        }
    } else {
        return 0;
    }
    return x;
}

int main() {
    return escolher(true);
}
