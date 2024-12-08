package main

import (
	"crypto/sha1"

	"fmt"

	"io"
	"log"
	"os"
	"path/filepath"
)

func dedupe_packages(rootPath string) {
	sha2path := make(map[string]string)
	err := filepath.Walk(rootPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			return nil
		}
		sha, err := shaSum(path)
		if err != nil {
			return err
		}
		if orig, exists := sha2path[sha]; exists {
			relPath, err := filepath.Rel(filepath.Dir(path), orig)
			if err != nil {
				return err
			}
			os.Remove(path)
			err = os.Symlink(relPath, path)
			if err != nil {
				return err
			}
			log.Printf("DEDUP: ln -sf %s %s\n", orig, path)
		} else {
			sha2path[sha] = path
		}
		return nil
	})
	if err != nil {
		log.Fatal(err)
	}
}

func shaSum(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()
	hash := sha1.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", hash.Sum(nil)), nil
}

func main() {
	if len(os.Args) != 2 {
		fmt.Println("Usage: dedupe_packages <directory_name>")
		os.Exit(1)
	}
	basePath := os.Args[1]
	dedupe_packages(basePath)
}
