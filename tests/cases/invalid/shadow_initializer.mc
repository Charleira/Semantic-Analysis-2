int main() {
    int x = 1;
    {
        int x = x;
        print(x);
    }
    return 0;
}
