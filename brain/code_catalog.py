"""Verified, secure reference implementations — multi-language code catalog."""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES: tuple[str, ...] = (
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "cpp",
)

CODE_TASKS: tuple[str, ...] = (
    "add_two_numbers",
    "is_palindrome",
    "fibonacci",
    "count_vowels",
    "merge_sorted",
)

# Hand-verified implementations: defensive edge cases, no unsafe APIs, iterative algorithms.
_CATALOG: dict[tuple[str, str], dict[str, str]] = {
    ("python", "add_two_numbers"): {
        "code": "def add(a, b):\n    return a + b",
        "tests": "assert add(2, 3) == 5\nassert add(-1, 1) == 0",
    },
    ("python", "is_palindrome"): {
        "code": (
            "def is_palindrome(s):\n"
            "    if s is None:\n"
            "        return False\n"
            "    text = str(s)\n"
            "    return text == text[::-1]"
        ),
        "tests": (
            "assert is_palindrome('racecar') is True\n"
            "assert is_palindrome('hello') is False\n"
            "assert is_palindrome('') is True"
        ),
    },
    ("python", "fibonacci"): {
        "code": (
            "def fib(n):\n"
            "    if not isinstance(n, int) or n < 0:\n"
            "        raise ValueError('n must be a non-negative integer')\n"
            "    if n <= 1:\n"
            "        return n\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b"
        ),
        "tests": "assert fib(0) == 0\nassert fib(1) == 1\nassert fib(10) == 55",
    },
    ("python", "count_vowels"): {
        "code": (
            "def count_vowels(s):\n"
            "    if s is None:\n"
            "        return 0\n"
            "    vowels = set('aeiouAEIOU')\n"
            "    return sum(1 for ch in str(s) if ch in vowels)"
        ),
        "tests": (
            "assert count_vowels('hello') == 2\n"
            "assert count_vowels('AEIOU') == 5\n"
            "assert count_vowels('xyz') == 0"
        ),
    },
    ("python", "merge_sorted"): {
        "code": (
            "def merge_sorted(a, b):\n"
            "    a = list(a or [])\n"
            "    b = list(b or [])\n"
            "    i = j = 0\n"
            "    out = []\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n"
            "            out.append(a[i])\n"
            "            i += 1\n"
            "        else:\n"
            "            out.append(b[j])\n"
            "            j += 1\n"
            "    return out + a[i:] + b[j:]"
        ),
        "tests": (
            "assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]\n"
            "assert merge_sorted([], [1]) == [1]\n"
            "assert merge_sorted([], []) == []"
        ),
    },
    ("javascript", "add_two_numbers"): {
        "code": "function add(a, b) {\n  return a + b;\n}",
        "tests": (
            "if (add(2, 3) !== 5) throw new Error('add(2,3)');\n"
            "if (add(-1, 1) !== 0) throw new Error('add(-1,1)');"
        ),
    },
    ("javascript", "is_palindrome"): {
        "code": (
            "function isPalindrome(s) {\n"
            "  if (s == null) return false;\n"
            "  const text = String(s);\n"
            "  return text === text.split('').reverse().join('');\n"
            "}"
        ),
        "tests": (
            "if (!isPalindrome('racecar')) throw new Error('racecar');\n"
            "if (isPalindrome('hello')) throw new Error('hello');\n"
            "if (!isPalindrome('')) throw new Error('empty');"
        ),
    },
    ("javascript", "fibonacci"): {
        "code": (
            "function fib(n) {\n"
            "  if (!Number.isInteger(n) || n < 0) throw new Error('invalid n');\n"
            "  if (n <= 1) return n;\n"
            "  let a = 0, b = 1;\n"
            "  for (let i = 2; i <= n; i += 1) {\n"
            "    const next = a + b;\n"
            "    a = b;\n"
            "    b = next;\n"
            "  }\n"
            "  return b;\n"
            "}"
        ),
        "tests": (
            "if (fib(0) !== 0) throw new Error('fib(0)');\n"
            "if (fib(1) !== 1) throw new Error('fib(1)');\n"
            "if (fib(10) !== 55) throw new Error('fib(10)');"
        ),
    },
    ("javascript", "count_vowels"): {
        "code": (
            "function countVowels(s) {\n"
            "  if (s == null) return 0;\n"
            "  const vowels = new Set(['a','e','i','o','u','A','E','I','O','U']);\n"
            "  let count = 0;\n"
            "  for (const ch of String(s)) {\n"
            "    if (vowels.has(ch)) count += 1;\n"
            "  }\n"
            "  return count;\n"
            "}"
        ),
        "tests": (
            "if (countVowels('hello') !== 2) throw new Error('hello');\n"
            "if (countVowels('AEIOU') !== 5) throw new Error('AEIOU');\n"
            "if (countVowels('xyz') !== 0) throw new Error('xyz');"
        ),
    },
    ("javascript", "merge_sorted"): {
        "code": (
            "function mergeSorted(a, b) {\n"
            "  const left = Array.isArray(a) ? a : [];\n"
            "  const right = Array.isArray(b) ? b : [];\n"
            "  const out = [];\n"
            "  let i = 0, j = 0;\n"
            "  while (i < left.length && j < right.length) {\n"
            "    if (left[i] <= right[j]) out.push(left[i++]);\n"
            "    else out.push(right[j++]);\n"
            "  }\n"
            "  return out.concat(left.slice(i), right.slice(j));\n"
            "}"
        ),
        "tests": (
            "const m1 = mergeSorted([1,3,5],[2,4,6]);\n"
            "if (JSON.stringify(m1) !== JSON.stringify([1,2,3,4,5,6])) throw new Error('m1');\n"
            "if (JSON.stringify(mergeSorted([], [1])) !== JSON.stringify([1])) throw new Error('m2');\n"
            "if (JSON.stringify(mergeSorted([], [])) !== JSON.stringify([])) throw new Error('m3');"
        ),
    },
    ("typescript", "add_two_numbers"): {
        "code": "function add(a: number, b: number): number {\n  return a + b;\n}",
        "tests": (
            "if (add(2, 3) !== 5) throw new Error('add(2,3)');\n"
            "if (add(-1, 1) !== 0) throw new Error('add(-1,1)');"
        ),
    },
    ("typescript", "is_palindrome"): {
        "code": (
            "function isPalindrome(s: string): boolean {\n"
            "  const text = String(s ?? '');\n"
            "  return text === text.split('').reverse().join('');\n"
            "}"
        ),
        "tests": (
            "if (!isPalindrome('racecar')) throw new Error('racecar');\n"
            "if (isPalindrome('hello')) throw new Error('hello');\n"
            "if (!isPalindrome('')) throw new Error('empty');"
        ),
    },
    ("typescript", "fibonacci"): {
        "code": (
            "function fib(n: number): number {\n"
            "  if (!Number.isInteger(n) || n < 0) throw new Error('invalid n');\n"
            "  if (n <= 1) return n;\n"
            "  let a = 0, b = 1;\n"
            "  for (let i = 2; i <= n; i += 1) {\n"
            "    const next = a + b;\n"
            "    a = b;\n"
            "    b = next;\n"
            "  }\n"
            "  return b;\n"
            "}"
        ),
        "tests": (
            "if (fib(0) !== 0) throw new Error('fib(0)');\n"
            "if (fib(10) !== 55) throw new Error('fib(10)');"
        ),
    },
    ("typescript", "count_vowels"): {
        "code": (
            "function countVowels(s: string): number {\n"
            "  const vowels = new Set(['a','e','i','o','u','A','E','I','O','U']);\n"
            "  let count = 0;\n"
            "  for (const ch of String(s ?? '')) {\n"
            "    if (vowels.has(ch)) count += 1;\n"
            "  }\n"
            "  return count;\n"
            "}"
        ),
        "tests": (
            "if (countVowels('hello') !== 2) throw new Error('hello');\n"
            "if (countVowels('AEIOU') !== 5) throw new Error('AEIOU');"
        ),
    },
    ("typescript", "merge_sorted"): {
        "code": (
            "function mergeSorted(a: number[], b: number[]): number[] {\n"
            "  const left = a ?? [];\n"
            "  const right = b ?? [];\n"
            "  const out: number[] = [];\n"
            "  let i = 0, j = 0;\n"
            "  while (i < left.length && j < right.length) {\n"
            "    if (left[i] <= right[j]) out.push(left[i++]);\n"
            "    else out.push(right[j++]);\n"
            "  }\n"
            "  return out.concat(left.slice(i), right.slice(j));\n"
            "}"
        ),
        "tests": (
            "const m1 = mergeSorted([1,3,5],[2,4,6]);\n"
            "if (JSON.stringify(m1) !== JSON.stringify([1,2,3,4,5,6])) throw new Error('m1');"
        ),
    },
    ("java", "add_two_numbers"): {
        "code": (
            "public final class Solution {\n"
            "  private Solution() {}\n"
            "  public static int add(int a, int b) {\n"
            "    return a + b;\n"
            "  }\n"
            "}"
        ),
        "tests": (
            "public final class SolutionTest {\n"
            "  public static void main(String[] args) {\n"
            "    assert Solution.add(2, 3) == 5;\n"
            "    assert Solution.add(-1, 1) == 0;\n"
            "  }\n"
            "}"
        ),
    },
    ("java", "is_palindrome"): {
        "code": (
            "public final class Solution {\n"
            "  private Solution() {}\n"
            "  public static boolean isPalindrome(String s) {\n"
            "    if (s == null) return false;\n"
            "    return s.contentEquals(new StringBuilder(s).reverse().toString());\n"
            "  }\n"
            "}"
        ),
        "tests": (
            "public final class SolutionTest {\n"
            "  public static void main(String[] args) {\n"
            "    assert Solution.isPalindrome(\"racecar\");\n"
            "    assert !Solution.isPalindrome(\"hello\");\n"
            "    assert Solution.isPalindrome(\"\");\n"
            "  }\n"
            "}"
        ),
    },
    ("java", "fibonacci"): {
        "code": (
            "public final class Solution {\n"
            "  private Solution() {}\n"
            "  public static int fib(int n) {\n"
            "    if (n < 0) throw new IllegalArgumentException(\"n must be non-negative\");\n"
            "    if (n <= 1) return n;\n"
            "    int a = 0, b = 1;\n"
            "    for (int i = 2; i <= n; i++) {\n"
            "      int next = a + b;\n"
            "      a = b;\n"
            "      b = next;\n"
            "    }\n"
            "    return b;\n"
            "  }\n"
            "}"
        ),
        "tests": (
            "public final class SolutionTest {\n"
            "  public static void main(String[] args) {\n"
            "    assert Solution.fib(0) == 0;\n"
            "    assert Solution.fib(10) == 55;\n"
            "  }\n"
            "}"
        ),
    },
    ("java", "count_vowels"): {
        "code": (
            "public final class Solution {\n"
            "  private Solution() {}\n"
            "  public static int countVowels(String s) {\n"
            "    if (s == null) return 0;\n"
            "    int count = 0;\n"
            "    for (char ch : s.toCharArray()) {\n"
            "      if (\"aeiouAEIOU\".indexOf(ch) >= 0) count += 1;\n"
            "    }\n"
            "    return count;\n"
            "  }\n"
            "}"
        ),
        "tests": (
            "public final class SolutionTest {\n"
            "  public static void main(String[] args) {\n"
            "    assert Solution.countVowels(\"hello\") == 2;\n"
            "    assert Solution.countVowels(\"AEIOU\") == 5;\n"
            "  }\n"
            "}"
        ),
    },
    ("java", "merge_sorted"): {
        "code": (
            "import java.util.ArrayList;\n"
            "import java.util.List;\n"
            "public final class Solution {\n"
            "  private Solution() {}\n"
            "  public static List<Integer> mergeSorted(List<Integer> a, List<Integer> b) {\n"
            "    List<Integer> left = a == null ? List.of() : a;\n"
            "    List<Integer> right = b == null ? List.of() : b;\n"
            "    List<Integer> out = new ArrayList<>();\n"
            "    int i = 0, j = 0;\n"
            "    while (i < left.size() && j < right.size()) {\n"
            "      if (left.get(i) <= right.get(j)) out.add(left.get(i++));\n"
            "      else out.add(right.get(j++));\n"
            "    }\n"
            "    while (i < left.size()) out.add(left.get(i++));\n"
            "    while (j < right.size()) out.add(right.get(j++));\n"
            "    return out;\n"
            "  }\n"
            "}"
        ),
        "tests": (
            "import java.util.List;\n"
            "public final class SolutionTest {\n"
            "  public static void main(String[] args) {\n"
            "    assert Solution.mergeSorted(List.of(1,3,5), List.of(2,4,6)).equals(List.of(1,2,3,4,5,6));\n"
            "  }\n"
            "}"
        ),
    },
    ("go", "add_two_numbers"): {
        "code": (
            "package solution\n\n"
            "func Add(a, b int) int {\n"
            "\treturn a + b\n"
            "}"
        ),
        "tests": (
            "package solution\n\n"
            "func ExampleAdd() bool {\n"
            "\treturn Add(2, 3) == 5 && Add(-1, 1) == 0\n"
            "}"
        ),
    },
    ("go", "is_palindrome"): {
        "code": (
            "package solution\n\n"
            "func IsPalindrome(s string) bool {\n"
            "\tfor i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {\n"
            "\t\tif s[i] != s[j] {\n"
            "\t\t\treturn false\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn true\n"
            "}"
        ),
        "tests": (
            "package solution\n\n"
            "func ExampleIsPalindrome() bool {\n"
            "\treturn IsPalindrome(\"racecar\") && !IsPalindrome(\"hello\") && IsPalindrome(\"\")\n"
            "}"
        ),
    },
    ("go", "fibonacci"): {
        "code": (
            "package solution\n\n"
            "func Fib(n int) int {\n"
            "\tif n < 0 {\n"
            "\t\tpanic(\"n must be non-negative\")\n"
            "\t}\n"
            "\tif n <= 1 {\n"
            "\t\treturn n\n"
            "\t}\n"
            "\ta, b := 0, 1\n"
            "\tfor i := 2; i <= n; i++ {\n"
            "\t\ta, b = b, a+b\n"
            "\t}\n"
            "\treturn b\n"
            "}"
        ),
        "tests": (
            "package solution\n\n"
            "func ExampleFib() bool {\n"
            "\treturn Fib(0) == 0 && Fib(10) == 55\n"
            "}"
        ),
    },
    ("go", "count_vowels"): {
        "code": (
            "package solution\n\n"
            "func CountVowels(s string) int {\n"
            "\tvowels := \"aeiouAEIOU\"\n"
            "\tcount := 0\n"
            "\tfor _, ch := range s {\n"
            "\t\tfor _, v := range vowels {\n"
            "\t\t\tif ch == v {\n"
            "\t\t\t\tcount++\n"
            "\t\t\t\tbreak\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn count\n"
            "}"
        ),
        "tests": (
            "package solution\n\n"
            "func ExampleCountVowels() bool {\n"
            "\treturn CountVowels(\"hello\") == 2 && CountVowels(\"AEIOU\") == 5\n"
            "}"
        ),
    },
    ("go", "merge_sorted"): {
        "code": (
            "package solution\n\n"
            "func MergeSorted(a, b []int) []int {\n"
            "\tif a == nil {\n"
            "\t\ta = []int{}\n"
            "\t}\n"
            "\tif b == nil {\n"
            "\t\tb = []int{}\n"
            "\t}\n"
            "\ti, j := 0, 0\n"
            "\tout := make([]int, 0, len(a)+len(b))\n"
            "\tfor i < len(a) && j < len(b) {\n"
            "\t\tif a[i] <= b[j] {\n"
            "\t\t\tout = append(out, a[i])\n"
            "\t\t\ti++\n"
            "\t\t} else {\n"
            "\t\t\tout = append(out, b[j])\n"
            "\t\t\tj++\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn append(append(out, a[i:]...), b[j:]...)\n"
            "}"
        ),
        "tests": (
            "package solution\n\n"
            "func ExampleMergeSorted() bool {\n"
            "\tr := MergeSorted([]int{1, 3, 5}, []int{2, 4, 6})\n"
            "\treturn len(r) == 6 && r[0] == 1 && r[5] == 6\n"
            "}"
        ),
    },
    ("rust", "add_two_numbers"): {
        "code": "pub fn add(a: i32, b: i32) -> i32 {\n    a + b\n}",
        "tests": (
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    #[test]\n"
            "    fn add_works() {\n"
            "        assert_eq!(add(2, 3), 5);\n"
            "        assert_eq!(add(-1, 1), 0);\n"
            "    }\n"
            "}"
        ),
    },
    ("rust", "is_palindrome"): {
        "code": (
            "pub fn is_palindrome(s: &str) -> bool {\n"
            "    let bytes = s.as_bytes();\n"
            "    let mut i = 0;\n"
            "    let mut j = bytes.len();\n"
            "    while i < j {\n"
            "        j -= 1;\n"
            "        if bytes[i] != bytes[j] {\n"
            "            return false;\n"
            "        }\n"
            "        i += 1;\n"
            "    }\n"
            "    true\n"
            "}"
        ),
        "tests": (
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    #[test]\n"
            "    fn palindrome_works() {\n"
            "        assert!(is_palindrome(\"racecar\"));\n"
            "        assert!(!is_palindrome(\"hello\"));\n"
            "    }\n"
            "}"
        ),
    },
    ("rust", "fibonacci"): {
        "code": (
            "pub fn fib(n: u32) -> u32 {\n"
            "    if n <= 1 {\n"
            "        return n;\n"
            "    }\n"
            "    let mut a = 0u32;\n"
            "    let mut b = 1u32;\n"
            "    for _ in 2..=n {\n"
            "        let next = a + b;\n"
            "        a = b;\n"
            "        b = next;\n"
            "    }\n"
            "    b\n"
            "}"
        ),
        "tests": (
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    #[test]\n"
            "    fn fib_works() {\n"
            "        assert_eq!(fib(0), 0);\n"
            "        assert_eq!(fib(10), 55);\n"
            "    }\n"
            "}"
        ),
    },
    ("rust", "count_vowels"): {
        "code": (
            "pub fn count_vowels(s: &str) -> usize {\n"
            "    s.chars().filter(|ch| matches!(ch, 'a'|'e'|'i'|'o'|'u'|'A'|'E'|'I'|'O'|'U')).count()\n"
            "}"
        ),
        "tests": (
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    #[test]\n"
            "    fn vowels_work() {\n"
            "        assert_eq!(count_vowels(\"hello\"), 2);\n"
            "        assert_eq!(count_vowels(\"AEIOU\"), 5);\n"
            "    }\n"
            "}"
        ),
    },
    ("rust", "merge_sorted"): {
        "code": (
            "pub fn merge_sorted(a: &[i32], b: &[i32]) -> Vec<i32> {\n"
            "    let mut i = 0usize;\n"
            "    let mut j = 0usize;\n"
            "    let mut out = Vec::with_capacity(a.len() + b.len());\n"
            "    while i < a.len() && j < b.len() {\n"
            "        if a[i] <= b[j] {\n"
            "            out.push(a[i]);\n"
            "            i += 1;\n"
            "        } else {\n"
            "            out.push(b[j]);\n"
            "            j += 1;\n"
            "        }\n"
            "    }\n"
            "    out.extend_from_slice(&a[i..]);\n"
            "    out.extend_from_slice(&b[j..]);\n"
            "    out\n"
            "}"
        ),
        "tests": (
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    #[test]\n"
            "    fn merge_works() {\n"
            "        assert_eq!(merge_sorted(&[1,3,5], &[2,4,6]), vec![1,2,3,4,5,6]);\n"
            "    }\n"
            "}"
        ),
    },
    ("cpp", "add_two_numbers"): {
        "code": "int add(int a, int b) {\n    return a + b;\n}",
        "tests": (
            "#include <cassert>\n"
            "int main() {\n"
            "  assert(add(2, 3) == 5);\n"
            "  assert(add(-1, 1) == 0);\n"
            "  return 0;\n"
            "}"
        ),
    },
    ("cpp", "is_palindrome"): {
        "code": (
            "#include <string>\n"
            "bool isPalindrome(const std::string& s) {\n"
            "  return std::equal(s.begin(), s.begin() + s.size() / 2, s.rbegin());\n"
            "}"
        ),
        "tests": (
            "#include <cassert>\n"
            "#include <string>\n"
            "int main() {\n"
            "  assert(isPalindrome(\"racecar\"));\n"
            "  assert(!isPalindrome(\"hello\"));\n"
            "  return 0;\n"
            "}"
        ),
    },
    ("cpp", "fibonacci"): {
        "code": (
            "int fib(int n) {\n"
            "  if (n < 0) return -1;\n"
            "  if (n <= 1) return n;\n"
            "  int a = 0, b = 1;\n"
            "  for (int i = 2; i <= n; ++i) {\n"
            "    int next = a + b;\n"
            "    a = b;\n"
            "    b = next;\n"
            "  }\n"
            "  return b;\n"
            "}"
        ),
        "tests": (
            "#include <cassert>\n"
            "int main() {\n"
            "  assert(fib(0) == 0);\n"
            "  assert(fib(10) == 55);\n"
            "  return 0;\n"
            "}"
        ),
    },
    ("cpp", "count_vowels"): {
        "code": (
            "#include <string>\n"
            "int countVowels(const std::string& s) {\n"
            "  int count = 0;\n"
            "  for (char ch : s) {\n"
            "    if (std::string(\"aeiouAEIOU\").find(ch) != std::string::npos) ++count;\n"
            "  }\n"
            "  return count;\n"
            "}"
        ),
        "tests": (
            "#include <cassert>\n"
            "#include <string>\n"
            "int main() {\n"
            "  assert(countVowels(\"hello\") == 2);\n"
            "  assert(countVowels(\"AEIOU\") == 5);\n"
            "  return 0;\n"
            "}"
        ),
    },
    ("cpp", "merge_sorted"): {
        "code": (
            "#include <vector>\n"
            "std::vector<int> mergeSorted(const std::vector<int>& a, const std::vector<int>& b) {\n"
            "  std::vector<int> out;\n"
            "  out.reserve(a.size() + b.size());\n"
            "  size_t i = 0, j = 0;\n"
            "  while (i < a.size() && j < b.size()) {\n"
            "    if (a[i] <= b[j]) out.push_back(a[i++]);\n"
            "    else out.push_back(b[j++]);\n"
            "  }\n"
            "  while (i < a.size()) out.push_back(a[i++]);\n"
            "  while (j < b.size()) out.push_back(b[j++]);\n"
            "  return out;\n"
            "}"
        ),
        "tests": (
            "#include <cassert>\n"
            "#include <vector>\n"
            "int main() {\n"
            "  auto r = mergeSorted({1,3,5},{2,4,6});\n"
            "  assert(r.size() == 6 && r[0] == 1 && r[5] == 6);\n"
            "  return 0;\n"
            "}"
        ),
    },
}


def get_catalog_entry(language: str, task: str) -> dict[str, str] | None:
    return _CATALOG.get((language, task))


def list_catalog_tasks(language: str) -> list[str]:
    return [task for lang, task in _CATALOG if lang == language]
